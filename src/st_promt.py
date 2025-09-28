import os
import aiohttp
import logging,time

logger = logging.getLogger(__name__)

file_path = os.environ.get("file_path")

url = os.environ.get("DRIVE_DOWNLOAD_URL")

LAST_MODIFIED_FILE = os.environ.get("LAST_MODIFIED_FILE")

async def get_drive_last_modified(url):
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
            # Логируем ответ
            logger.info(f"HEAD Response: {response}")
                
            last_modified = response.headers.get('Last-Modified')
            logger.info(f"Last-Modified: {last_modified}")
                
            if last_modified:
                try:
                    timestamp = time.mktime(time.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z'))
                    logger.info(f"Timestamp: {timestamp}")
                    return timestamp
                except ValueError as e:
                    logger.info(f"Ошибка парсинга даты '{last_modified}': {e}")
                    return None
            return None

async def download_file():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
                logger.info(f"Файл успешно скачан и сохранён в: {file_path}")
                return True
            else:
                logger.info(f"Ошибка скачивания: статус {response.status}")
                return False

def get_saved_last_modified(current_time):
    if os.path.exists(LAST_MODIFIED_FILE):
        with open(LAST_MODIFIED_FILE, 'r') as f:
            try:
                return float(f.read().strip())
            except ValueError:
                save_last_modified(current_time)
                logger.info(f"Файл с сохраненной датой содержит невалидное значение. Файл '{LAST_MODIFIED_FILE}' **перезаписан** текущим timestamp: {current_time}.")
                return False
    save_last_modified(current_time)
    logger.info(f"Файл с сохраненной датой не найден. Создан новый файл '{LAST_MODIFIED_FILE}' с текущим timestamp: {current_time}.")
    return False

def save_last_modified(timestamp):
    with open(LAST_MODIFIED_FILE, 'w') as f:
        f.write(str(timestamp))
    logger.info(f"Новый timestamp {timestamp} сохранен.")
        
async def check_file_update():
    logger.info("Запускаем проверку обновления файла...")
    current_last_modified = await get_drive_last_modified(url)
    logger.info(f"Текущая дата изменения (timestamp): {current_last_modified}")
    
    if current_last_modified is None:
        logger.info("Не удалось получить дату изменения.")
        return

    saved_last_modified = get_saved_last_modified(current_last_modified)
    if saved_last_modified:
    	logger.info(f"Сохраненная дата изменения (timestamp): {saved_last_modified}")
    else:
        if current_last_modified > saved_last_modified:
            logger.info("Файл изменился! Запускаем скачивание и сохранение новой даты.")
            success = await download_file()
            if success:
                save_last_modified(current_last_modified)
                return True
        else:
            logger.info("Файл не изменился.")
            return False