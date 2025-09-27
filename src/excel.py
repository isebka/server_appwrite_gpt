import logging
import gspread
from appwrite.exception import AppwriteException
from oauth2client.service_account import ServiceAccountCredentials
import os,json,re, base64
import time
from appwrite.query import Query
from appwrite.client import Client
from appwrite.services.databases import Databases


logger = logging.getLogger(__name__)

client_app = (
        Client()
        .set_endpoint(os.environ.get("APPWRITE_FUNCTION_API_ENDPOINT"))
        .set_project(os.environ.get("APPWRITE_FUNCTION_PROJECT_ID"))
        .set_key(os.environ.get("x-appwrite-key"))
        )

databases = Databases(client_app)
# Настройки
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Новый код: Получаем JSON-строку из env и парсим в dict
creds_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if not creds_json_str:
    raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable is not set!")
try:
    json_str = base64.b64decode(creds_json_str).decode('utf-8')
    creds_dict = json.loads(json_str)  # Преобразуем строку в dict
except json.JSONDecodeError:
    raise ValueError("Invalid JSON in GOOGLE_CREDENTIALS_JSON!")

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)
GMAIL_RE = re.compile(
    r"^(?=.{1,254}$)(?=.{1,64}@)[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:gmail\.com|googlemail\.com)$",
    re.IGNORECASE
)

def is_gmail_address(s: str) -> bool:
    return bool(GMAIL_RE.match(s.strip()))

def create_coloum(spreadsheet_id, year_month):  # year_month = "2025-09"
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        try:
            delsh = spreadsheet.worksheet("Sheet1")
            spreadsheet.del_worksheet(delsh)
        except gspread.exceptions.WorksheetNotFound:
            try:
                sheet = spreadsheet.worksheet(year_month)
            except gspread.exceptions.WorksheetNotFound:
                sheet = spreadsheet.add_worksheet(title=year_month, rows=1000, cols=6)

                # Добавь заголовки с новым порядком
                sheet.update(
                    range_name='A1:H1',
                    values=[['Дата', 'Время', 'Тип', 'Сумма', 'Валюта', 'Категория', 'Описание', 'Неделя']],
                    value_input_option='USER_ENTERED'  # Для безопасности, но для текста не обязательно
                )
                # НЕ добавляем формулу здесь — сделаем при добавлении транзакций
            return sheet



    except Exception as e:
        print(e)
        logger.info(f"Ошибка в создание колон: {e}")

def add_transaction(spreadsheet_id, data):
    try:
        sheet = create_coloum(spreadsheet_id, time.strftime('%Y-%m'))

        # Найди следующую пустую строку
        row = len(sheet.get_all_values()) + 1

        # Запиши данные (A:H)
        sheet.update(
            range_name=f'A{row}:H{row}',
            values=[[time.strftime('%Y-%m-%d'), time.strftime('%H:%M'), data.get('type', ''), data.get('amount', ''), data.get('currency', ''), data.get('category', ''), data.get('comment', '')]],
            value_input_option='USER_ENTERED'
        )

        # Добавь формулу для недели в F{row}
        sheet.update(
            range_name=f'H{row}',
            values=[['=WEEKNUM(A' + str(row) + ')']],
            value_input_option='USER_ENTERED'  # Важно для формул
        )
        return 1
    except Exception as e:
        logger.info(f"Ошибка в добавление: {e}")


def check_available(user_id):
    if not user_id:
        return None
    try:
        result = databases.list_documents(
            database_id=os.environ.get("APPWRITE_DATABASE_ID"),
            collection_id=os.environ.get("APPWRITE_COLLECTION_ID"),
            queries=[Query.equal("userid", str(user_id))]  # Использование Query.equal вместо строки
        )
        return {"user_id": result.get("documents")[0].get("userid"), "spreadsheet_id": result.get("documents")[0].get("spreadsheet_id")}
    except IndexError:
        return None



def give_permision(user_id, email):
    if not email:
        return None
    if is_gmail_address(email):
        result = databases.list_documents(
            database_id=os.environ.get("APPWRITE_DATABASE_ID"),
            collection_id=os.environ.get("APPWRITE_COLLECTION_ID"),
            queries=[Query.equal("email", str(email))]  # Использование Query.equal вместо строки
        )
        res = check_available(user_id)
        if result['total'] == 0: # 0 - аккаунта не существует
            sh = client.open_by_key(res.get("spreadsheet_id"))
            sh.share(email, perm_type='user',
                                 role='writer')  # Делишь с сервисным аккаунтом
            return True
        else: # 1 - если аккаунт существует
            return False
    else:
        return None


def create_user_spreadsheet(user_id):
    try:
        spreadsheet_id = client.create(f"History_Finances_{user_id}")  # Создаёт новый spreadsheet
        databases.create_document(
            database_id=os.environ.get("APPWRITE_DATABASE_ID"),
            collection_id=os.environ.get("APPWRITE_COLLECTION_ID"),
            document_id="unique()",
            data={
                "userid": str(user_id),
                "spreadsheet_id": spreadsheet_id.id
            }
        )

        return spreadsheet_id


    except AppwriteException as a:
        print(f"Ошибка Appwrite: {a.message}")
        return None
    except Exception as e:
        logger.info(f"Ошибка Appwrite: {e}")



def excel_manager(text,user_id):
    try:
        if not user_id or not text:
            return None
        ch = check_available(user_id)
        logger.info(ch)
        if not ch: # Пользователя не сушествует
            spreadsheet_id = create_user_spreadsheet(user_id)
            add_transaction(spreadsheet_id, text)
            return True
        else:
            return add_transaction(ch.get("spreadsheet_id"), text)
    except Exception as e:
        logger.error("Ошибка обработчика excel", e)
