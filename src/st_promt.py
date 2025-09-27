import os
import aiohttp
import logging

logger = logging.getLogger(__name__)

file_path = os.environ.get("file_path")

url = os.environ.get("DRIVE_DOWNLOAD_URL")

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
