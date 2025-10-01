import os, json
import logging
import asyncio
import aio_pika
import threading
from .gpt_sort import gpt_response
from .st_promt import download_file
from .excel import excel_manager, check_available, give_permision

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

def process_message(user_id, text: str):
    try:
        logger.info(f"Фоновая задача: Начало обработки для пользователя {user_id}.")

        async def inner_async():
            await gpt_response(text=text, user_id=user_id)

        asyncio.run(inner_async()) 

        logger.info("Фоновая задача: Сообщение успешно отправлено в очередь 'gpt_sort'.")

    except Exception as e:
        logger.error(f"Фоновая задача: Ошибка при обработке для пользователя {user_id}: {e}", exc_info=True)

async def main(context):
    logger.info('main start')

    if context.req.method == "POST" and context.req.path == "/run":
        try:
            try:
                body = context.req.body_json
            except:
                body = context.req.body
            user_id = body.get("user_id")
            # Запуск в фоне
            background_thread = threading.Thread(
                target=process_message,
                args=(user_id, body.get('text_to_process')),  # Передаём body как text
                name=f"Worker-{user_id}",
                daemon=True  # Чтобы не блокировал shutdown
            )
            background_thread.start()

            logger.info(f"Вебхук для пользователя {user_id} принят. Запущена фоновая задача.")

            # Немедленно возвращаем ответ
            return context.res.json({"status": "Accepted for processing"}, 202)

        except Exception as e:
            logger.error(f"Ошибка при запуске фоновой задачи: {e}", exc_info=True)
            return context.res.json({"error": "Failed to start processing task"}, 500)

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
            email = data.get("email")
            user_id = data.get("user_id")
            if not email or not user_id:
                return context.res.json({"error": "user_id and email are required"})

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


