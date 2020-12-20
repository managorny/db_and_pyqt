import configparser
import os
import select
import socket
import sys
import json
import threading
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from server.server_ui import MainWindow, HistoryWindow, ConfigWindow, gui_create_model, create_stat_model
import logs.log_configs.server_log_config
import logging
from logs.log_configs.server_log_config import stream_handler  # - для теста в консоли.
from decorators import log

from common.default_conf import *
from common.utils import get_message, send_message

from metaclasses import ServerVerifier

from server.server_db import ServerStorage

logger = logging.getLogger('messengerapp_server')

# stream_handler.setLevel(logging.INFO)   # - для теста в консоли.

# Флаг о том, что был подключён новый пользователь нужен, чтобы не мучать базу данных
# постоянными запросами на обновление
new_connection = False
connection_lock = threading.Lock()


# дескриптор на проверку порта
class CheckPort:
    def __set__(self, instance, value):
        try:
            if not 1024 < value < 65536:
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
        global new_connection
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
                with connection_lock:
                    new_connection = True
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
            return list_of_messages.append(message)

        elif ACTION in message and message[ACTION] == GET_CONTACTS and \
                TIME in message and USER in message and \
                self.account_names_list[message[USER][ACCOUNT_NAME]] == client_with_message:
            response = {RESPONSE: 202, 'contacts_list': None}
            response['contacts_list'] = self.server_database.contacts_list(message[USER][ACCOUNT_NAME])
            send_message(client_with_message, response)

        elif ACTION in message and message[ACTION] == ADD_CONTACT and \
                TIME in message and USER in message and CONTACT in message and \
                self.account_names_list[message[USER][ACCOUNT_NAME]] == client_with_message:
            self.server_database.add_contact(message[USER][ACCOUNT_NAME], message[CONTACT][ACCOUNT_NAME])
            response = {RESPONSE: 200}
            # print(message)
            # print(message[USER][ACCOUNT_NAME], message[CONTACT][ACCOUNT_NAME])
            # print(response)
            send_message(client_with_message, response)

        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and \
                TIME in message and USER in message and CONTACT in message and \
                self.account_names_list[message[USER][ACCOUNT_NAME]] == client_with_message:
            self.server_database.remove_contact(message[USER][ACCOUNT_NAME], message[CONTACT][ACCOUNT_NAME])
            response = {RESPONSE: 200}
            send_message(client_with_message, response)

        elif ACTION in message and message[ACTION] == USERS_LIST and USER in message \
                and self.account_names_list[message[USER][ACCOUNT_NAME]] == client_with_message:
            response = {RESPONSE: 202, 'users_list': [user[0] for user in self.server_database.select_users()]}
            send_message(client_with_message, response)

        elif ACTION in message and message[ACTION] == 'exit' and ACCOUNT_NAME in message:
            clients_list.remove(account_names_list[message[ACCOUNT_NAME]])
            self.server_database.user_logout(message[ACCOUNT_NAME])
            clients_list[message[ACCOUNT_NAME]].close()
            del clients_list[message[ACCOUNT_NAME]]
            with connection_lock:
                new_connection = True
            return

        else:
            error = send_message(client_with_message, {
                RESPONSE: 400,
                ERROR: 'Bad Request'
            })
            logger.info(error)
            return error


@log
def load_params(default_port, default_address):
    # валидация и загрузка порта
    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            listen_port = default_port
    except IndexError:
        logger.error('После параметра -\'p\' необходимо указать номер порта.')
        sys.exit(1)

    # валидация и загрузка адреса
    try:
        if '-address' in sys.argv:
            listen_address = sys.argv[sys.argv.index('-address') + 1]
        else:
            listen_address = default_address

    except IndexError:
        logger.error('После параметра -\'address\'- необходимо указать адрес, который будет слушать сервер.')
        sys.exit(1)
    return listen_address, listen_port


def make_sock_get_msg_send_answer():
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/server/{'server_config.ini'}")

    # Загрузка параметров командной строки, если нет параметров, то задаём
    # значения по умоланию.
    listen_address, listen_port = load_params(
        int(config['SETTINGS']['default_port']), config['SETTINGS']['listen_address'])

    # Инициализация базы данных
    server_database = ServerStorage(
        os.path.join(
            config['SETTINGS']['database_path'],
            config['SETTINGS']['database_file']))

    # -p 8081 -address 192.168.1.109 (при проверке: работает как через терминал, так и через PyCharm)
    # listen_address, listen_port = load_params()
    # server_database = ServerStorage()

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
        elif cmd == 'contacts':
            usr = input('Введите username/login пользователя: ')
            for contact in sorted(server_database.contacts_list(usr)):
                print(f'Контакт - {contact}')
        elif cmd == 'add_contact':
            owner = input('Кому добавить новый контакт: ')
            new_contact = input('Введите username нового контакта: ')
            server_database.add_contact(owner, new_contact)
        elif cmd == 'exit':
            print('Завершение работы')
            break
        elif cmd == 'help':
            print('users - список юзеров,\n'
                  'active_users - список активных юзеров,\n'
                  'history - история посещений юзера\n'
                  'contacts - cписок контактов юзера\n'
                  'add_contact - добавить контакт\n' 
                  'exit - выход')
        else:
            print('Неверная команда, ведите help для получения списка команд')

    # создание графического интерфейса
    server_app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.statusBar().showMessage('Server working')
    main_window.active_users_table.setModel(gui_create_model(server_database))
    main_window.active_users_table.resizeColumnsToContents()
    main_window.active_users_table.resizeRowsToContents()

    # функция для обновления списка активных юзеров в зависимости от флага (новый коннекшн или нет)
    def list_update():
        global new_connection
        if new_connection:
            main_window.active_users_table.setModel(
                gui_create_model(server_database))
            main_window.active_users_table.resizeColumnsToContents()
            main_window.active_users_table.resizeRowsToContents()
            with connection_lock:
                new_connection = False

    # функция, создающяя окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.login_history_table.setModel(create_stat_model(server_database))
        stat_window.login_history_table.resizeColumnsToContents()
        stat_window.login_history_table.resizeRowsToContents()
        stat_window.show()

    # Функция сохранения настроек сервера
    def save_server_config():
        global config_window
        message = QMessageBox()
        config['SETTINGS']['database_path'] = config_window.db_path.text()
        config['SETTINGS']['database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            config['SETTINGS']['listen_address'] = config_window.ip.text()
            if 1023 < port < 65536:
                config['SETTINGS']['default_port'] = str(port)
                print(port)
                with open('server/server_config.ini', 'w') as conf:
                    config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка', 'Порт должен быть от 1024 до 65535')

    # Функция создающяя окно с настройками сервера
    def server_config():
        global config_window
        config_window = ConfigWindow()
        config_window.db_path.insert(config['SETTINGS']['database_path'])
        config_window.db_file.insert(config['SETTINGS']['database_file'])
        config_window.port.insert(config['SETTINGS']['default_port'])
        config_window.ip.insert(config['SETTINGS']['listen_address'])
        config_window.save_button.clicked.connect(save_server_config)

    # таймер для обновления списка раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связь кнопок с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_button.triggered.connect(server_config)

    # Запуск GUI
    server_app.exec_()


if __name__ == '__main__':
    make_sock_get_msg_send_answer()
