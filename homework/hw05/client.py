import sys
import logs.log_configs.client_log_config
import logging
# from logs.log_configs.client_log_config import stream_handler # - для теста в консоли.
import argparse
import threading
from PyQt5.QtWidgets import QApplication

from common.default_conf import *
from common.metaclasses import ClientVerifier
from common.decorators import log

from client.client_db import ClientStorage
from client.interaction import ClientInteraction
from client.client_main_window import ClientMainWindow
from client.qdialogs import UsernameDialog

logger = logging.getLogger('messengerapp_client')
# stream_handler.setLevel(logging.INFO)   # - для теста в консоли.


def load_params():  # TODO try to use argparse
    try:
        name = ''
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


def make_sock_send_msg_get_answer():
    # 192.168.1.109 8081 (при проверке: работает как через терминал, так и через PyCharm)

    server_address, server_port, client_account_name = load_params()

    client_app = QApplication(sys.argv)

    if not client_account_name:
        start_dialog = UsernameDialog()
        client_app.exec_()
        if start_dialog.ok_pressed:
            client_account_name = start_dialog.client_name.text()
            del start_dialog
        else:
            exit(0)

    logger.info(
        f'Запущен клиент с парамертами: адрес сервера - {server_address}, '
        f'порт - {server_port}, режим работы - {client_account_name}')

    database = ClientStorage(client_account_name)

    try:
        sock = ClientInteraction(server_address, server_port, client_account_name, database)

        # response = get_response(get_message(sock))
        # logger.info(f'Установлено соединение с сервером. Ответ: {response}')
        # print(f'Установлено соединение с сервером.')
    except Exception as ex:
        print(ex)
        exit(1)

    sock.setDaemon(True)
    sock.start()

    main_window = ClientMainWindow(database, sock)
    main_window.make_connection(sock)
    main_window.setWindowTitle(f'Чат Программа alpha release - {client_account_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт
    sock.socket_shutdown()
    sock.join()


if __name__ == '__main__':
    make_sock_send_msg_get_answer()
