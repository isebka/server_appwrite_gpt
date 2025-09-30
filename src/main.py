import os, json
import logging
import asyncio
import aio_pika
from gpt_sort import gpt_response
from st_promt import download_file
from excel import excel_manager, check_available, give_permision

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

# Функция для обработки очереди RabbitMQ при cron-триггере
async def consume_queue():
    url = os.environ.get("RABBITMQ_URL")
    if not url:
        logger.error("CLOUDAMQP_URL не задан в переменных окружения")
        return

    try:
        connection = await aio_pika.connect_robust(url)
        async with connection:
            channel = await connection.channel()
            queue_name = "gpt_sort"  # Измените на реальное имя очереди, если нужно
            queue = await channel.declare_queue(queue_name, durable=True)

            while True:
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        if message is None:
                            break
                        try:
                            data = json.loads(message.body.decode())
                            user_id = data.get("user_id")
                            text = data.get("text_to_process")
                            if user_id and text:
                                success = await process_message(text, user_id)
                                if success:
                                    await message.ack()
                                else:
                                    await message.nack(requeue=True)
                            else:
                                logger.warning("Некорректные данные в сообщении")
                                await message.nack(requeue=True)
                        except json.JSONDecodeError as e:
                            logger.error(f"Ошибка декодирования JSON в сообщении: {e}")
                            await message.nack(requeue=True)
                        except Exception as e:
                            logger.error(f"Ошибка обработки сообщения из очереди: {e}", exc_info=True)
                            await message.nack(requeue=True)
        logger.info("Обработка очереди завершена")
    except Exception as e:
        logger.error(f"Ошибка подключения к RabbitMQ: {e}", exc_info=True)

# Основная функция, вызываемая Appwrite
async def main(context):
    logger.info('main start')
    logger.info(context.req.headers)

    # Проверка на cron-триггер (schedule)
    if context.req.headers.get("x-appwrite-trigger") == "schedule":
        await consume_queue()
        return context.res.send("Cron task completed", 200)

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
            data = json.loads(context.req.body)  # Парсим JSON из строки
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


