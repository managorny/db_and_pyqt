import sys
import json
import socket
import time
import logs.log_configs.client_log_config
import logging
# from logs.log_configs.client_log_config import stream_handler # - для теста в консоли.
from decorators import log
import argparse
import threading

from common.default_conf import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    RESPONSE, ERROR, DEFAULT_IP_ADDRESS, DEFAULT_PORT, MESSAGE, MESSAGE_CLIENT, FROM, TO, INFO
from common.utils import get_message, send_message

from metaclasses import ClientVerifier

logger = logging.getLogger('messengerapp_client')
# stream_handler.setLevel(logging.INFO)   # - для теста в консоли.

account_name = 'Demo'


class SendingClient(threading.Thread, metaclass=ClientVerifier):

    def __init__(self, sock, client_account_name):
        self.sock = sock
        self.client_account_name = client_account_name
        super().__init__()

    # @log # пришлось убрать декоратор, т.к. dis.get_instructions не показывает использование функций
    def create_message(self, from_user, to_user, client_message):
        message = {
            ACTION: MESSAGE,
            TIME: time.time(),
            FROM: {
                ACCOUNT_NAME: from_user
            },
            TO: {
                ACCOUNT_NAME: to_user

            },
            MESSAGE_CLIENT: client_message,
        }
        return message

    # @log # пришлось убрать декоратор, т.к. dis.get_instructions не показывает использование функции get_message
    def run(self):
        while True:
            action = input("Введите команду: ")
            if action == 'message':
                to_user = input('Введите получателя сообщения: ')
                client_message = input("Введите сообщение для отправки: ")
                send_message(self.sock, self.create_message(self.client_account_name, to_user, client_message))
            elif action == 'exit' or action == 'Q':
                exit_message = {ACTION: 'exit', TIME: time.time(), ACCOUNT_NAME: account_name}
                send_message(self.sock, exit_message)
                logger.info("Завершение работы по запросу.")
                print("Программа завершена")
                time.sleep(0.5)
                break
            elif action == 'help' or action == '-h' or action == 'h':
                print("Возможны команды: message - отправить сообщение;\n"
                      "exit или Q - выйти;\n"
                      "help - повторно вызвать данное сообщение.")
            else:
                print("Введена не верная команда. Введите help для получения списка команд.")


class GettingClient(threading.Thread, metaclass=ClientVerifier):

    def __init__(self, sock, client_account_name):
        self.sock = sock
        self.client_account_name = client_account_name
        super().__init__()

    # @log # пришлось убрать декоратор, т.к. dis.get_instructions не показывает использование функции get_message
    def run(self):
        while True:
            response = get_message(self.sock)
            if ACTION in response and FROM in response and MESSAGE_CLIENT in response \
                    and response[ACTION] == MESSAGE and FROM in response and \
                    TO in response and response[TO][ACCOUNT_NAME] == self.client_account_name:
                sender = response[FROM][ACCOUNT_NAME]
                text_message = response[MESSAGE_CLIENT]
                print(f'\nПолучено сообщение от {sender}, текст сообщения: {text_message}\nВведите команду: ')
                logger.info(f'Получено сообщение от {sender}, текст сообщения: {text_message}')
            else:
                logger.error(f'Не удается распознать ответ от сервера: {response}')


@log
def get_response(message):
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            response = '200 : OK'
            logger.info(response)
            return response
        error = f'400 : {message[ERROR]}'
        logger.info(error)
        return error
    raise logger.error(ValueError)


@log
def create_presence_message(client_account_name):
    presence_message = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: client_account_name,
            INFO: 'very good user'
        }
    }
    logger.info(f'Сообщение о присутствии пользователя {client_account_name} сформировано')
    return presence_message


@log
def load_params():  # TODO try to use argparse
    try:
        name = 'Demo8' # можно использвать для отладки в Pycharm, иначе падает если юзер не в списке подключенных
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        if '-n' in sys.argv:
            name = sys.argv[sys.argv.index('-n') + 1]
        if server_port < 1024 or server_port > 65535:
            raise ValueError
    except IndexError:
        logger.warning('Использованы дефолтные адрес и порт')
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
    except ValueError:
        logger.critical('В качестве порта может быть указано только число в диапазоне от 1024 до 65535.')
        sys.exit(1)

    return server_address, server_port, name


def clients_socket(server_address, server_port, client_account_name):
    # Инициализация сокета и обмен
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_address, server_port))
    message_to_server = create_presence_message(client_account_name)
    send_message(sock, message_to_server)
    return sock


# Основная функция
def make_sock_send_msg_get_answer():
    # 192.168.1.109 8081 (при проверке: работает как через терминал, так и через PyCharm)

    server_address, server_port, client_account_name = load_params()

    if not client_account_name:
        client_account_name = input('Введите имя пользователя: ')

    logger.info(
        f'Запущен клиент с парамертами: адрес сервера - {server_address}, '
        f'порт - {server_port}, режим работы - {client_account_name}')

    sock = clients_socket(server_address, server_port, client_account_name)

    try:
        get_response(get_message(sock))
    except (ValueError, json.JSONDecodeError):
        logger.error('Не удалось декодировать сообщение сервера.')
    else:
        getting_thread = GettingClient(sock, client_account_name)
        getting_thread.daemon = True
        getting_thread.start()

        sending_thread = SendingClient(sock, client_account_name)
        sending_thread.daemon = True
        sending_thread.start()

        while True:
            time.sleep(1)
            if getting_thread.is_alive() and sending_thread.is_alive():
                continue
            break


if __name__ == '__main__':
    make_sock_send_msg_get_answer()
