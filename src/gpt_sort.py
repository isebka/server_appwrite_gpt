from g4f.client import Client
import os,json, logging
from .excel import excel_manager
from .st_promt import check_file_update

file_path = os.environ.get("file_path")

logger = logging.getLogger(__name__)

def gpt_response(text, user_id, attempt=1, max_attempts=3):
    logging.info("start gpt fun")
    if not text or not user_id:
        return None
    try:

        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        modified_content = content.replace('[ТЕКСТ_ЗДЕСЬ]', text)
        
        logging.info("start gpt fun2")
        client = Client()
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": modified_content}],
            web_search=False
        )
        # Parse the string content as JSON
        content_str = response.choices[0].message.content
        logging.info(content_str)
        try:
            content_dict = json.loads(content_str)  # This converts the string to a dict
            excel_manager(content_dict, user_id)  # Now pass the dict to your function
        except json.JSONDecodeError:
            logger.info("Error: The response content is not valid JSON:", content_str)
    except Exception:
        logging.info("check")
        if attempt < max_attempts:
            check_file_update()
            return gpt_response(text, user_id, attempt + 1, max_attempts)
        else:
            logging.error(f"Попытки исчерпаны ({max_attempts}). Не удалось получить GPT-ответ.")
            return None


