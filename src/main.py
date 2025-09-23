import os
import logging
#import asyncio
#import aio_pika
#import gpt_sort



# Настройка логирования
log_file = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),  # Запись в файл
        logging.StreamHandler()       # Вывод в консоль
    ]
)
logger = logging.getLogger(__name__)




async def start():
    try:
        connection = await aio_pika.connect_robust(os.environ.get("RABBITMQ_URL"))
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue("gpt_sort", durable=True)
            logger.info("Starting RabbitMQ consumer...")
            await queue.consume()
            await asyncio.Future()
    except Exception as e:
        logger.error(f"Consumer connection error: {e}", exc_info=True)




# Основная функция, вызываемая Appwrite
async def main(context):
    logger.info('main start1')
    logger.info('main start2')
    logger.info('main start3')
    logger.info('main start4')

    if context.req.method == "GET" and context.req.path == "/run":
            #asyncio.create_task()
            return context.res.json({"status": "Consumer started and running"})


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
                "Hello from the Appwrite function! Use /start_consumer to run the RabbitMQ listener.")











