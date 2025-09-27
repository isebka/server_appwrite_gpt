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
            print(response)
            last_modified = response.headers.get('Last-Modified')
            print(f"Last-Modified: {last_modified}")
            if last_modified:
                try:
                    # Преобразуем в timestamp
                    timestamp = time.mktime(time.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z'))
                    print(f"Timestamp: {timestamp}")
                    return timestamp
                except ValueError as e:
                    print(f"Ошибка парсинга даты: {e}")
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

def get_saved_last_modified():
    if os.path.exists(LAST_MODIFIED_FILE):
        with open(LAST_MODIFIED_FILE, 'r') as f:
            try:
                return float(f.read().strip())
            except ValueError:
                return 0
    return 0

def save_last_modified(timestamp):
    with open(LAST_MODIFIED_FILE, 'w') as f:
        f.write(str(timestamp))
        
async def check_file_update():
    current_last_modified = await get_drive_last_modified(url)  # Теперь с await
    print(current_last_modified)
    if current_last_modified is None:
        print("Не удалось получить дату изменения.")
        return

    saved_last_modified = get_saved_last_modified()
    if current_last_modified > saved_last_modified:
        print("Файл изменился! Отправляем уведомления.")
        await download_file()
        save_last_modified(current_last_modified)

    else:
        print("Файл не изменился.")