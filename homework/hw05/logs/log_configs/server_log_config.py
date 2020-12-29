import os
import sys
from pathlib import Path
import logging
import logging.handlers

# готовим путь до нужной папки с файлами логов
path_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
# path_dir = Path(os.path.dirname(os.path.abspath(sys.argv[0]))).parent # для запуска из самого файла
# path_dir_files_logs = 'log_files/server_logs' # для запуска из самого файла
path_dir_files_logs = 'logs/log_files/server_logs'
path_file = os.path.join(path_dir, path_dir_files_logs, 'server.log')

# создаем логгер, его уровень и формат
logger = logging.getLogger('messengerapp_server')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(name)s - %(message)s')

# хэндлер в файл
file_handler = logging.handlers.TimedRotatingFileHandler(path_file, encoding='utf-8', when='D', interval=1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# хэндлер в поток
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

if __name__ == '__main__':
    logger.info('Проверка отправки обычной информации')
    logger.error('Проверка отправки ошибки')
    logger.debug('Debug')
    logger.warning('Предупреждение')
    logger.critical('Критическая ситуация')
