import sys
import logging
import logs.log_configs.client_log_config
import logs.log_configs.server_log_config
import inspect

if sys.argv[0].find('client.py') >= 0:
    logger = logging.getLogger('messengerapp_client')
elif sys.argv[0].find('server.py') >= 0:
    logger = logging.getLogger('messengerapp_server')


# В виде функции
def log(function):
    def wrapper(*args, **kwargs):
        result = function(*args, **kwargs)
        logger.debug(
            f'Функция {function.__name__}, аргументы - {args}, {kwargs}, результат - {result} | '
            f'Вызов из функции "{inspect.currentframe().f_back.f_code.co_name}"', stacklevel=2)
        return result

    return wrapper

# В виде класса
# class Log:
#     def __call__(self, function):
#         def wrapper(*args, **kwargs):
#             result = function(*args, **kwargs)
#             logger.debug(f'Функция {function.__name__}, аргументы - {args}, {kwargs}, результат - {result} | '
#                          f'Вызов из функции "{inspect.currentframe().f_back.f_code.co_name}"', stacklevel=2)
#             return result
#         return wrapper
