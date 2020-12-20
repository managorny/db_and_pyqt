import sys
import json
import socket
import time
import logging
import threading
from PyQt5.QtCore import pyqtSignal, QObject

sys.path.append('../')
from common.default_conf import *
from common.utils import *

logger = logging.getLogger('messengerapp_client')

# Объект блокировки сокета и работы с базой данных
socket_lock = threading.Lock()
database_lock = threading.Lock()


class ClientInteraction(threading.Thread, QObject):
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, ip, port, client_account_name, client_database):

        threading.Thread.__init__(self)
        QObject.__init__(self)

        self.sock = ip
        self.port = port
        self.client_account_name = client_account_name
        self.client_database = client_database
        self.sock = None
        self.connection_init(ip, port)

        try:
            self.get_users_list()
            self.get_contacts_list()
        except OSError as err:
            if err.errno:
                logger.critical(f'Потеряно соединение с сервером.')
            logger.error('Timeout соединения при обновлении списков пользователей.')
        except json.JSONDecodeError:
            logger.critical(f'Потеряно соединение с сервером.')
            # Флаг продолжения работы взаимодействия.
        self.running = True

    def connection_init(self, ip, port):

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)

        # если удалось соедиться, ставим флаг True
        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения {i + 1}')
            try:
                self.sock.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            time.sleep(1)

        # Если соединится не удалось - исключение
        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            raise Exception

        logger.debug('Установлено соединение с сервером')

        # Отправляем сообщение о присутствии и получаем ответ, иначе исключение
        try:
            with socket_lock:
                send_message(self.sock, self.create_presence_message())
                self.get_response(get_message(self.sock))
        except (OSError, json.JSONDecodeError):
            logger.critical('Потеряно соединение с сервером!')
            raise Exception

        # Если все ок, то пишем соответствующее сообщение
        logger.info('Соединение с сервером успешно установлено.')

    # @log # пришлось убрать декоратор, т.к. dis.get_instructions не показывает использование функций
    def create_presence_message(self):
        presence_message = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username,
                INFO: 'very good user'
            }
        }
        logger.info(f'Сообщение о присутствии пользователя {self.username} сформировано')
        return presence_message

    def get_response(self, message):
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                response = '200 : OK'
                logger.info(response)
                return response
            error = message[ERROR]
        elif message[RESPONSE] == 400:
            logger.error(error)
        else:
            logger.debug(f'Принят неизвестный код подтверждения {message[RESPONSE]}')

        # Если это сообщение от пользователя добавляем в базу, даём сигнал о новом сообщении
        if ACTION in message and FROM in message and MESSAGE_CLIENT in message \
                and message[ACTION] == MESSAGE and FROM in message and \
                TO in message and message[TO][ACCOUNT_NAME] == self.username:
            sender = message[FROM][ACCOUNT_NAME]
            text_message = message[MESSAGE_CLIENT]
            to_user = message[TO][ACCOUNT_NAME]
            logger.debug(f'Получено сообщение от {sender}, текст сообщения: {text_message}')
            with database_lock:
                self.client_database.save_message(self.username, to_user, text_message)
            self.new_message.emit(message[sender])

    def send_new_message(self, to_user, message):
        with socket_lock:
            send_message(self.sock, self.create_message(self.username, to_user, message))
            self.get_response(get_message(self.sock))
            logger.info(f'Отправлено сообщение для пользователя {to_user}')

    def create_message(self, to_user, client_message):
        with database_lock:
            if not self.client_database.check_user(to_user):
                logger.error(f'Попытка отправить сообщение незарегистрированому пользователю: {to_user}')
                return
        message = {
            ACTION: MESSAGE,
            TIME: time.time(),
            FROM: {
                ACCOUNT_NAME: self.username
            },
            TO: {
                ACCOUNT_NAME: to_user

            },
            MESSAGE_CLIENT: client_message,
        }
        return message

    def get_users_list(self):
        logger.debug(f'Запрос списка известных пользователей {self.username}')
        request_message = {
            ACTION: USERS_LIST,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username
            },
        }
        logger.debug(f'Сформирован запрос {request_message}')

        with socket_lock:
            send_message(self.sock, request_message)
            response = get_message(self.sock)
        if RESPONSE in response and 'users_list' in response:
            self.client_database.add_known_users(response['users_list'])
        else:
            logger.error('Не удалось обновить список известных пользователей.')

    def get_contacts_list(self):
        logger.debug(f'Запрос списка контактов для пользователя {self.username}')
        request = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username,
            }
        }
        logger.debug(f'Сформирован запрос {request}')
        with socket_lock:
            send_message(self.sock, request)
            response = get_message(self.sock)
        logger.debug(f'Получен ответ {response}')
        if RESPONSE in response and 'contacts_list' in response:
            for contact in response['users_list']:
                self.client_database.add_contact(contact)
        else:
            logger.error('Не удалось обновить список контактов.')

    # Функция добавления пользователя в контакт лист
    def add_contact(self, contact):
        logger.debug(f'Создание контакта {contact}')
        request_message = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username,
            },
            CONTACT: {
                ACCOUNT_NAME: contact,
            },
        }
        # print(username, contact)
        # print(request_message)
        with socket_lock:
            send_message(self.sock, request_message)
            response = self.get_response(get_message(self.sock))
        # print(response)
        if RESPONSE in response and response[RESPONSE] == 200:
            pass
        else:
            raise print('Ошибка создания контакта')
        print('Успешное создание контакта')

    # Функция удаления пользователя из списка контактов
    def remove_contact(self, contact):
        logger.debug(f'Создание контакта {contact}')
        request_message = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.username,
            },
            CONTACT: {
                ACCOUNT_NAME: contact,
            },
        }
        with socket_lock:
            send_message(self.sock, request_message)
            response = self.get_response(get_message(self.sock))
        if RESPONSE in response and response[RESPONSE] == 200:
            pass
        else:
            raise print('Ошибка удаления контакта')
        print('Успешное удаление контакта')

    def get_history(self, command):
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

    def socket_shutdown(self):
        self.running = False
        exit_message = {ACTION: 'exit', TIME: time.time(), ACCOUNT_NAME: self.username}
        with socket_lock:
            try:
                send_message(self.sock, exit_message)
            except OSError:
                pass
        logger.debug('Взаимодействие завершено.')
        time.sleep(0.5)

    def run(self):
        logger.debug('Запущена приемка сообщений с сервера.')
        time.sleep(1)
        with socket_lock:
            try:
                self.sock.settimeout(0.5)
                response = get_message(self.sock)
            except Exception as ex:
                logger.error(f'Не удалось декодировать полученное сообщение.')
                self.running = False
                self.connection_lost.emit()
            except OSError as err:
                if err.errno:
                    logger.critical(f'Содениенение с сервером потеряно.')
                    self.running = False
                    self.connection_lost.emit()
            except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                logger.critical(f'Содениенение с сервером потеряно.')
                self.running = False
                self.connection_lost.emit()
            else:
                logger.debug(f'Принято сообщение с сервера: {response}')
                self.get_response(response)
            finally:
                self.sock.settimeout(5)
