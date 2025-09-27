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


def ober_message():
    async def message_sort(message: aio_pika.IncomingMessage):
            try:
                gpt_response(text=message.body.decode("utf-8"), user_id=message.headers.get("user_id"))
                await message.ack()
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
                await message.nack(requeue=True)
    return message_sort


async def start():
    try:
        connection = await aio_pika.connect_robust(os.environ.get("RABBITMQ_URL"))
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue("gpt_sort", durable=True)
            logger.info("Starting RabbitMQ consumer...")

            message_sort = ober_message()
            processed_count = 0
            while True:
                try:
                    message = await queue.get(no_ack=False, timeout=5)
                except aio_pika.exceptions.QueueEmpty:
                    logger.info("Queue is empty, stopping consumer.")
                    break
                try:
                    await message_sort(message)
                    processed_count += 1
                    logger.info(f"Processed {processed_count} messages.")
                except Exception as e:
                    logger.info(f"Eror in batch processing : {e}", exc_info=True)
                    await message.nack(requeue=True)

    except Exception as e:
        logger.error(f"Consumer connection error: {e}", exc_info=True)


# Основная функция, вызываемая Appwrite
async def main(context):
    logger.info('main start')
    if context.req.method == "GET" and context.req.path == "/run":
        await start()
        return context.res.json({"status": "Consumer started and running"})
    if context.req.method == "GET" and context.req.path == "/promt":
        await asyncio.create_task(download_file())
        return context.res.json({"status": "Promt replait"})

    if context.req.method == "GET" and context.req.path == "/url":
        try:
            user_id = context.req.query.get("user_id")
            if not user_id:
                return context.res.json({"error": "user_id is required"}, status=400)
            ch = check_available(user_id)
            if not ch.get("spreadsheet_id"):
                return context.res.json({"error": "No spreadsheet found"}, status=404)
            return context.res.json({"url": "https://docs.google.com/spreadsheets/d/" + ch.get("spreadsheet_id")},
                                    status=200)
        except Exception as e:
            logger.error(f"Error: {e}")
            return context.res.json({"error": str(e)}, status=500)

    # Второй эндпоинт: POST /add_email
    if context.req.method == "POST" and context.req.path == "/add_email":
        try:
            body = json.loads(context.req.body)
            email = body.get("email")
            user_id = body.get("user_id")
            if not email or not user_id:
                return context.res.json({"error": "user_id and email are required"}, status=400)

            # Асинхронно запускаем задачу (если сервер поддерживает asyncio)
            gh = give_permision(user_id, email)
            if not gh:
                return context.res.json({"status": "Email access"}, status=200)
            return context.res.json({"status": "Email processed successfully"}, status=200)
        except json.JSONDecodeError:
            return context.res.json({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"Error: {e}")
            return context.res.json({"error": str(e)}, status=500)

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





