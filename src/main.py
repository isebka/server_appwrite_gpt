import os, json
import logging
import asyncio
import aio_pika
from .gpt_sort import gpt_response

from .st_promt import download_file

from .excel import excel_manager,check_available,give_permision



# Настройка логирования
log_file = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),  # Запись в файл
        logging.StreamHandler()       # Вывод в консоль
    ])
logger = logging.getLogger(__name__)


# Функция обработки сообщения (адаптирована из ober_message)
async def process_message(text: str, user_id: str):
    try:
        logger.info("message processing start")
        await gpt_response(text=text, user_id=user_id)  # Если gpt_response async, добавьте await
        return True  # Успех
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        return False  # Ошибка



# Основная функция, вызываемая Appwrite
async def main(context):
    logger.info('main start')
    logger.info(context.req)

    if context.req.method == "POST" and context.req.path == "/run":
        try:
            data = json.loads(context.req.body)
            logger.info(f"data2d: {data}")
            user_id = data.get("user_id")
            text = data.get("text_to_process")
            logger.info(f"fal: {user_id}|{text}")
            success = await process_message(text=text, user_id=user_id)
            if success:
                return context.res.send("OK", 200)  # Ack: сообщение удалено
            else:
                return context.res.send("Error", 500)  # Retry: CloudAMQP повторит
        except Exception as e:
            logger.error(f"Ошибка в POST-обработке: {e}", exc_info=True)
            return context.res.send("Internal Error", 500)  # Retry

    if context.req.method == "GET" and context.req.path == "/promt":
        await asyncio.create_task(download_file())
        return context.res.json({"status": "Promt replait"})

    if context.req.method == "GET" and context.req.path == "/url":
        try:
            user_id = context.req.query.get("user_id")
            if not user_id:
                return context.res.json({"error": "user_id is required"})
            ch = check_available(user_id)
            if not ch.get("spreadsheet_id"):
                return context.res.json({"error": "No spreadsheet found"})
            return context.res.json({"url": "https://docs.google.com/spreadsheets/d/" + ch["spreadsheet_id"]})
        except Exception as e:
            logger.error(f"Error: {e}")
            return context.res.json({"error": str(e)})

    if context.req.method == "POST" and context.req.path == "/add_email":
        try:
            data = context.req.body  
        
            # Проверяем, является ли data словарем, как ожидается
            if not isinstance(data, dict):
                # Если это не словарь, возможно, тело запроса пустое или не JSON
                logger.error(f"context.req.body is not a dict, but: {type(data)}")
                return context.req.json({"error": "Request body is missing or not a dictionary."})

            # Извлекаем данные из словаря
            email = data.get("email")
            user_id = data.get("user_id")
            if not email or not user_id:
                return context.res.json({"error": "user_id and email are required"})

            # Асинхронно запускаем задачу (если сервер поддерживает asyncio)
            gp = give_permision(user_id, email)
            if not gp:
            	return context.res.json({"status": "Email already"})
            return context.res.json({"status": "Email successfully"})
        except json.JSONDecodeError:
            return context.res.json({"error": "Invalid JSON"})
        except Exception as e:
            logger.error(f"Error: {e}")
            return context.res.json({"error": str(e)})

    # Новый эндпоинт для вывода логов
    if context.req.method == "GET" and context.req.path == "/logs":
        try:
            with open(log_file, "r") as f:
                logs_content = f.read()
            # Отправляем содержимое файла как текст
            return context.res.text(logs_content)
        except FileNotFoundError:
            return context.res.text("Log file not found.", status=404)
        except Exception as e:
            logger.error(f"Failed to read log file: {e}")
            return context.res.text("Error reading log file.", status=500)
    return context.res.text(
                "Hello from the Appwrite function! Use /run to run the RabbitMQ listener.")





