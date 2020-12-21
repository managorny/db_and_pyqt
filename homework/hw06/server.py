import configparser
import os
import sys
import threading
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

import logs.log_configs.server_log_config
import logging
from common.decorators import log
from common.default_conf import *
from server.server_db import ServerStorage
from server.server_core import Server
from server.main_window import MainWindow


logger = logging.getLogger('messengerapp_server')

# stream_handler.setLevel(logging.INFO)   # - для теста в консоли.

# Флаг о том, что был подключён новый пользователь нужен, чтобы не мучать базу данных
# постоянными запросами на обновление
new_connection = False
connection_lock = threading.Lock()


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
    try:
        if '--no_gui' in sys.argv:
            gui_flag = True
        else:
            gui_flag = False
    except Exception as ex:
        logger.error(f'{ex}')
        sys.exit(1)

    return listen_address, listen_port, gui_flag


def make_sock_get_msg_send_answer():
    config = configparser.ConfigParser()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{dir_path}/server/{'server_config.ini'}")

    # Загрузка параметров командной строки, если нет параметров, то задаём
    # значения по умоланию.
    listen_address, listen_port, gui_flag = load_params(
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

    # # Добавим команды для получения результатов из базы (работает пока не запущен хотя бы один клиент)
    # while True:
    #     cmd = input('Введите комманду: ')
    #     if cmd == 'users':
    #         for usr in sorted(server_database.select_users()):
    #             print(f'Пользователь с логином {usr[0]}, дата создания - {usr[1]}, последний вход - {usr[1]}')
    #     elif cmd == 'active_users':
    #         for usr in sorted(server_database.select_active_users()):
    #             print(f'Активный пользователь {usr[0]}, ip - {usr[1]}, port - {usr[2]}, дата и время входа - {usr[3]}')
    #     elif cmd == 'history':
    #         usr = input('Введите username/login пользователя: ')
    #         for hist in sorted(server_database.login_history_user(usr)):
    #             print(f'Юзер - {hist[0]}, дата входа - {hist[1]}, ip - {hist[2]}, port - {hist[3]}')
    #     elif cmd == 'contacts':
    #         usr = input('Введите username/login пользователя: ')
    #         for contact in sorted(server_database.contacts_list(usr)):
    #             print(f'Контакт - {contact}')
    #     elif cmd == 'add_contact':
    #         owner = input('Кому добавить новый контакт: ')
    #         new_contact = input('Введите username нового контакта: ')
    #         server_database.add_contact(owner, new_contact)
    #     elif cmd == 'exit':
    #         print('Завершение работы')
    #         break
    #     elif cmd == 'help':
    #         print('users - список юзеров,\n'
    #               'active_users - список активных юзеров,\n'
    #               'history - история посещений юзера\n'
    #               'contacts - cписок контактов юзера\n'
    #               'add_contact - добавить контакт\n'
    #               'exit - выход')
    #     else:
    #         print('Неверная команда, ведите help для получения списка команд')

    # Если указан параметр без GUI, то запускаем обработчик консольного ввода
    if gui_flag:
        while True:
            command = input('Введите exit для завершения работы сервера.')
            if command == 'exit':
                # Если выход, то завршаем основной цикл сервера.
                server.running = False
                server.join()
                break

    # Если не указан запуск без GUI, то запускаем GUI:
    else:
        # Создаём графическое окуружение для сервера:
        server_app = QApplication(sys.argv)
        server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
        main_window = MainWindow(server_database, server, config)

        # Запускаем GUI
        server_app.exec_()

        # По закрытию окон останавливаем обработчик сообщений
        server.running = False


if __name__ == '__main__':
    make_sock_get_msg_send_answer()
