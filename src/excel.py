import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os,json
import time

# Настройки
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Новый код: Получаем JSON-строку из env и парсим в dict
creds_dict = os.environ.get("GOOGLE_CREDENTIALS_JSON")

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)

def get_or_create_month_sheet(spreadsheet_id, year_month):  # year_month = "2025-09"
    spreadsheet = client.open_by_key(spreadsheet_id)
    try:
        sheet = spreadsheet.worksheet(year_month)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=year_month, rows=1000, cols=6)
        # Добавь заголовки с новым порядком
        sheet.update(
            range_name='A1:G1',
            values=[['Дата', 'Тип', 'Сумма', 'Валюта', 'Категория', 'Описание', 'Неделя']],
            value_input_option='USER_ENTERED'  # Для безопасности, но для текста не обязательно
        )
        # НЕ добавляем формулу здесь — сделаем при добавлении транзакций
    return sheet

def add_transaction(data):
    sheet = get_or_create_month_sheet(SPREADSHEET_ID, time.strftime('%Y-%m'))

    # Найди следующую пустую строку
    row = len(sheet.get_all_values()) + 1

    # Запиши данные (A:E)
    sheet.update(
        range_name=f'A{row}:F{row}',
        values=[[time.strftime('%d-%m-%Y %H:%M'), data.get('type', ''), data.get('amount', ''), data.get('currency', ''), data.get('category', ''), data.get('comment', '')]],
        value_input_option='USER_ENTERED'
    )

    # Добавь формулу для недели в F{row}
    sheet.update(
        range_name=f'G{row}',
        values=[['=WEEKNUM(A' + str(row) + ')']],
        value_input_option='USER_ENTERED'  # Важно для формул
    )