import select
import socket
import sys
import json
import threading
import time
import logs.log_configs.server_log_config
import logging
from logs.log_configs.server_log_config import stream_handler  # - для теста в консоли.
from decorators import log

from common.default_conf import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    RESPONSE, ERROR, DEFAULT_IP_ADDRESS, DEFAULT_PORT, MAX_CONNECTIONS, \
    FROM, MESSAGE, MESSAGE_CLIENT, TO, INFO
from common.utils import get_message, send_message

from metaclasses import ServerVerifier

from server_db import ServerStorage

logger = logging.getLogger('messengerapp_server')

# stream_handler.setLevel(logging.INFO)   # - для теста в консоли.


# дескриптор на проверку порта
class CheckPort:
    def __set__(self, instance, value):
        try:
            if not 1024 < value < 65535:
                raise ValueError
        except ValueError:
            logger.critical('В качастве порта может быть указано только число в диапазоне от 1024 до 65535.')
            sys.exit(1)
        instance.__dict__[self.my_attr] = value

    def __set_name__(self, owner_class, my_attr):
        self.my_attr = my_attr


class Server (threading.Thread, metaclass=ServerVerifier):

    port = CheckPort()

    def __init__(self, listen_address, listen_port, server_database):
        self.address = listen_address
        self.port = listen_port
        self.clients = []
        self.messages = []
        self.account_names_list = {}
        self.server_database = server_database
        super().__init__()

    def socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.address, self.port))
        self.sock.settimeout(0.5)
        self.sock.listen(MAX_CONNECTIONS)

    def run(self):
        self.socket()

        while True:
            try:
                client, client_address = self.sock.accept()
            except socket.error:
                pass
            else:
                logger.info(f'Установлено соедение с клиентом {client_address}')
                self.clients.append(client)

            get_message_list = []
            send_message_list = []
            # self.errors_list = []

            try:
                if self.clients:
                    get_message_list, send_message_list, errors_list = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            if get_message_list:
                info = 'good client' # ЗАГЛУШКА ДЛЯ ТЕСТА ПЕРЕДАЧИ ДОП ПАРАМЕТРА В БАЗУ
                for client_with_message in get_message_list:
                    try:
                        self.process_client_message(get_message(client_with_message),
                                                    self.messages, client_with_message,
                                                    self.clients, self.account_names_list, info)
                    except Exception as ex:
                        print(ex)
                        logger.info(f'Потеряно соединение с клиентом {client_with_message.getpeername()}.')
                        self.clients.remove(client_with_message)

            for msg in self.messages:
                try:
                    self.prc_message(msg, self.account_names_list, send_message_list)
                except Exception:
                    logger.info(f'Потеряно соединение с клиентом {msg[TO][ACCOUNT_NAME]}.')
                    self.clients.remove(self.account_names_list[msg[TO][ACCOUNT_NAME]])
                    del self.account_names_list[msg[TO][ACCOUNT_NAME]]
            self.messages.clear()

    # обработка сообщения
    @log
    def prc_message(self, msg, account_names_list, send_message_list):
        if msg[FROM][ACCOUNT_NAME] in account_names_list and \
                account_names_list[msg[TO][ACCOUNT_NAME]] in send_message_list:
            send_message(account_names_list[msg[TO][ACCOUNT_NAME]], msg)

            logger.info(f'Cообщение отправлено пользователю {msg[TO][ACCOUNT_NAME]} '
                        f'от пользователя {msg[FROM][ACCOUNT_NAME]}.')
        elif msg[TO][ACCOUNT_NAME] in account_names_list and \
                account_names_list[msg[TO][ACCOUNT_NAME]] not in send_message_list:
            raise ConnectionError
        else:
            logger.error(
                f'Пользователь {msg[TO][ACCOUNT_NAME]} не существует, отправка сообщения невозможна.')

    # пришем сообщения от пользователя
    @log
    def process_client_message(self, message, list_of_messages, client_with_message, clients_list, account_names_list,
                               info):
        logger.debug(f'Разбор сообщения от клиента {client_with_message}')

        if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
                and USER in message:
            if message[USER][ACCOUNT_NAME] not in account_names_list.keys():
                self.account_names_list[message[USER][ACCOUNT_NAME]] = client_with_message
                client_ip_address, client_port = client_with_message.getpeername()
                info = message[USER][INFO]
                # print(client_ip_address, client_port, info)
                self.server_database.user_login(message[USER][ACCOUNT_NAME], info, client_ip_address, client_port)
                answer = send_message(client_with_message, {RESPONSE: 200})
                logger.info(answer)
            else:
                response = {RESPONSE: 400, ERROR: 'Пользователь с таким именем уже существует.'}
                send_message(client_with_message, response)
                clients_list.remove(client_with_message)
                client_with_message.close()
            return

        elif ACTION in message and message[ACTION] == MESSAGE and \
                TIME in message and MESSAGE_CLIENT in message and \
                FROM in message and TO in message:
            # print(message[FROM][ACCOUNT_NAME], message[TO][ACCOUNT_NAME])
            self.server_database.contacts(message[FROM][ACCOUNT_NAME], message[TO][ACCOUNT_NAME])
            return list_of_messages.append(message)

        elif ACTION in message and message[ACTION] == 'exit' and ACCOUNT_NAME in message:
            clients_list.remove(account_names_list[message[ACCOUNT_NAME]])
            self.server_database.user_logout(message[ACCOUNT_NAME])
            clients_list[message[ACCOUNT_NAME]].close()
            del clients_list[message[ACCOUNT_NAME]]
            return

        else:
            error = send_message(client_with_message, {
                RESPONSE: 400,
                ERROR: 'Bad Request'
            })
            logger.info(error)
            return error


@log
def load_params():
    # валидация и загрузка порта
    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            listen_port = DEFAULT_PORT
    except IndexError:
        logger.error('После параметра -\'p\' необходимо указать номер порта.')
        sys.exit(1)

    # валидация и загрузка адреса
    try:
        if '-address' in sys.argv:
            listen_address = sys.argv[sys.argv.index('-address') + 1]
        else:
            listen_address = DEFAULT_IP_ADDRESS

    except IndexError:
        logger.error('После параметра -\'address\'- необходимо указать адрес, который будет слушать сервер.')
        sys.exit(1)
    return listen_address, listen_port


def make_sock_get_msg_send_answer():
    # -p 8081 -address 192.168.1.109 (при проверке: работает как через терминал, так и через PyCharm)
    listen_address, listen_port = load_params()

    server_database = ServerStorage()

    server = Server(listen_address, listen_port, server_database)
    server.daemon = True
    server.start()

    # Добавим команды для получения результатов из базы (работает пока не запущен хотя бы один клиент)
    while True:
        cmd = input('Введите комманду: ')
        if cmd == 'users':
            for usr in sorted(server_database.select_users()):
                print(f'Пользователь с логином {usr[0]}, дата создания - {usr[1]}, последний вход - {usr[1]}')
        elif cmd == 'active_users':
            for usr in sorted(server_database.select_active_users()):
                print(f'Активный пользователь {usr[0]}, ip - {usr[1]}, port - {usr[2]}, дата и время входа - {usr[3]}')
        elif cmd == 'history':
            usr = input('Введите username/login пользователя: ')
            for hist in sorted(server_database.login_history_user(usr)):
                print(f'Юзер - {hist[0]}, дата входа - {hist[1]}, ip - {hist[2]}, port - {hist[3]}')
        elif cmd == 'exit':
            print('Завершение работы')
            break
        elif cmd == 'help':
            print('users - список юзеров,\n'
                  'active_users - список активных юзеров,\n'
                  'history - история посещений юзера\n'
                  'exit - выход')
        else:
            print('Неверная команда, ведите help для получения списка команд')


if __name__ == '__main__':
    make_sock_get_msg_send_answer()
