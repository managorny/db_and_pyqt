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

from common.default_conf import *
from common.utils import get_message, send_message

from metaclasses import ClientVerifier

from client_db import ClientStorage

logger = logging.getLogger('messengerapp_client')
# stream_handler.setLevel(logging.INFO)   # - для теста в консоли.

account_name = 'Demo'

# Объект блокировки сокета и работы с базой данных
sock_lock = threading.Lock()
database_lock = threading.Lock()


class SendingClient(threading.Thread, metaclass=ClientVerifier):

    def __init__(self, sock, client_account_name, client_database):
        self.sock = sock
        self.client_account_name = client_account_name
        self.client_database = client_database
        super().__init__()

    # @log # пришлось убрать декоратор, т.к. dis.get_instructions не показывает использование функций
    def create_message(self, from_user, to_user, client_message):
        with database_lock:
            if not self.client_database.check_user(to_user):
                logger.error(f'Попытка отправить сообщение незарегистрированому пользователю: {to_user}')
                return
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

                # Сохраняем сообщения для истории
                with database_lock:
                    self.client_database.save_message(self.client_account_name, to_user, client_message)

                # Необходимо дождаться освобождения сокета для отправки сообщения
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_message(self.client_account_name, to_user, client_message))
                        logger.info(f'Отправлено сообщение для пользователя {to_user}')
                    except OSError as err:
                        if err.errno:
                            logger.critical('Потеряно соединение с сервером')
                            exit(1)
                        else:
                            logger.error('Не удалось передать сообщение. Таймаут')

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
                      "help - повторно вызвать данное сообщение;\n"
                      "contacts - список контактов;\n"
                      "edit_contacts - редактирование списка контактов;\n"
                      "history - история сообщений")

            elif action == 'contacts':
                with database_lock:
                    contacts_list = self.client_database.get_contacts()
                for contact in contacts_list:
                    print(contact)

            elif action == 'edit_contacts':
                self.edit_contacts()

            elif action == 'history':
                self.get_history()

            else:
                print("Введена не верная команда. Введите help для получения списка команд.")

    def edit_contacts(self):
        action = input('Для удаления введите delete, для добавления add: ')
        if action == 'add':
            new_contact = input('Введите username нового контакта: ')
            if self.client_database.check_user(new_contact):
                with database_lock:
                    self.client_database.add_contact(new_contact)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.client_account_name, new_contact)
                    except Exception as ex:
                        logger.error('Не удалось отправить информацию на сервер.')
        elif action == 'delete':
            contact_to_remove = input('Введите username удаляемного контакта: ')
            with database_lock:
                if self.client_database.check_contact(contact_to_remove):
                    self.client_database.remove_contact(contact_to_remove)
                else:
                    logger.error('Попытка удаления несуществующего контакта.')
            with sock_lock:
                try:
                    remove_contact(self.sock, self.client_account_name, contact_to_remove)
                except Exception as ex:
                    logger.error('Не удалось отправить информацию на сервер.')

    def get_history(self):
        command = input('Показать входящие сообщения - in, исходящие - out, все - all: ')
        with database_lock:
            if command == 'in':
                history_list = self.client_database.get_message_history(to_user=self.client_account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} от {message[3]}:\n{message[2]}')
            elif command == 'out':
                history_list = self.client_database.get_message_history(from_user=self.client_account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} от {message[3]}:\n{message[2]}')
            elif command == 'all':
                history_list = self.client_database.get_message_history()
                for message in history_list:
                    print(f'\nСообщение от пользователя: '
                          f'{message[0]}, пользователю {message[1]} от {message[3]}\n{message[2]}')


class GettingClient(threading.Thread, metaclass=ClientVerifier):

    def __init__(self, sock, client_account_name, client_database):
        self.sock = sock
        self.client_account_name = client_account_name
        self.client_database = client_database
        super().__init__()

    # @log # пришлось убрать декоратор, т.к. dis.get_instructions не показывает использование функции get_message
    def run(self):
        time.sleep(1)
        while True:
            try:
                response = get_message(self.sock)
            except Exception as ex:
                logger.error(f'Не удалось декодировать полученное сообщение.')
            except OSError as err:
                if err.errno:
                    logger.critical(f'Содениенение с сервером потеряно.')
                    break
            except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                logger.critical(f'Содениенение с сервером потеряно.')
                break
            else:
                if ACTION in response and FROM in response and MESSAGE_CLIENT in response \
                        and response[ACTION] == MESSAGE and FROM in response and \
                        TO in response and response[TO][ACCOUNT_NAME] == self.client_account_name:
                    sender = response[FROM][ACCOUNT_NAME]
                    text_message = response[MESSAGE_CLIENT]
                    print(f'\nПолучено сообщение от {sender}, текст сообщения: {text_message}\nВведите команду: ')
                    logger.info(f'Получено сообщение от {sender}, текст сообщения: {text_message}')
                    with database_lock:
                        try:
                            self.client_database.save_message(response[sender], self.client_account_name,
                                                              response[text_message])
                        except Exception as ex:
                            print(ex)
                            logger.error(f'Ошибка взаимодействия с базой данных - {ex}')
                else:
                    if response == {'response': 200}:
                        pass
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
        name = 'Demo8'  # можно использвать для отладки в Pycharm, иначе падает если юзер не в списке подключенных
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


def get_contacts_list(sock, username):
    logger.debug(f'Запрос списка контактов для пользователя {username}')
    request = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: username,
        }
    }
    logger.debug(f'Сформирован запрос {request}')
    send_message(sock, request)
    response = get_message(sock)
    logger.debug(f'Получен ответ {response}')
    if RESPONSE in response and 'contacts_list' in response:
        return response['contacts_list']
    else:
        raise Exception


# Функция добавления пользователя в контакт лист
def add_contact(sock, username, contact):
    logger.debug(f'Создание контакта {contact}')
    request_message = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: username,
        },
        CONTACT: {
            ACCOUNT_NAME: contact,
        },
    }
    # print(username, contact)
    # print(request_message)
    send_message(sock, request_message)
    response = get_message(sock)
    # print(response)
    if RESPONSE in response and response[RESPONSE] == 200:
        pass
    else:
        raise print('Ошибка создания контакта')
    print('Успешное создание контакта')


# Функция удаления пользователя из списка контактов
def remove_contact(sock, username, contact):
    logger.debug(f'Создание контакта {contact}')
    request_message = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: username,
        },
        CONTACT: {
            ACCOUNT_NAME: contact,
        },
    }
    send_message(sock, request_message)
    response = get_message(sock)
    if RESPONSE in response and response[RESPONSE] == 200:
        pass
    else:
        raise print('Ошибка удаления контакта')
    print('Успешное удаление контакта')


def get_users_list(sock, username):
    logger.debug(f'Запрос списка известных пользователей {username}')
    request_message = {
        ACTION: USERS_LIST,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: username
        },
    }
    send_message(sock, request_message)
    response = get_message(sock)
    if RESPONSE in response and 'users_list' in response:
        return response['users_list']
    else:
        raise Exception


# Загрузка данных из базы
def load_db(sock, client_database, username):
    try:
        users_list = get_users_list(sock, username)
    except Exception as ex:
        logger.error(f'Ошибка запроса списка известных пользователей.\n{ex}')
    else:
        client_database.add_known_users(users_list)

    try:
        contacts_list = get_contacts_list(sock, username)
    except Exception as ex:
        logger.error(f'Ошибка запроса списка контактов.\n{ex}')
    else:
        if contacts_list is not None:
            for contact in contacts_list:
                client_database.add_contact(contact)


# Основная функция
def make_sock_send_msg_get_answer():
    # 192.168.1.109 8081 (при проверке: работает как через терминал, так и через PyCharm)

    server_address, server_port, client_account_name = load_params()

    if not client_account_name:
        client_account_name = input('Введите имя пользователя: ')

    logger.info(
        f'Запущен клиент с парамертами: адрес сервера - {server_address}, '
        f'порт - {server_port}, режим работы - {client_account_name}')
    try:
        sock = clients_socket(server_address, server_port, client_account_name)
        response = get_response(get_message(sock))
        logger.info(f'Установлено соединение с сервером. Ответ: {response}')
        print(f'Установлено соединение с сервером.')
    except (ValueError, json.JSONDecodeError):
        logger.error('Не удалось декодировать сообщение сервера.')
    except (ConnectionRefusedError, ConnectionError):
        logger.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}.')
        exit(1)
    else:

        client_database = ClientStorage(client_account_name)
        load_db(sock, client_database, client_account_name)

        getting_thread = GettingClient(sock, client_account_name, client_database)
        getting_thread.daemon = True
        getting_thread.start()

        sending_thread = SendingClient(sock, client_account_name, client_database)
        sending_thread.daemon = True
        sending_thread.start()

        while True:
            time.sleep(1)
            if getting_thread.is_alive() and sending_thread.is_alive():
                continue
            break


if __name__ == '__main__':
    make_sock_send_msg_get_answer()
