import os
import sys
import json

from Cryptodome.PublicKey import RSA
import logs.log_configs.client_log_config
import logging
import argparse
from PyQt5.QtWidgets import QApplication, QMessageBox

from common.default_conf import *
from common.decorators import log

from client.client_db import ClientStorage
from client.interaction import ClientInteraction
from client.client_main_window import ClientMainWindow
from client.qdialogs import UsernameDialog

logger = logging.getLogger('messengerapp_client')


# stream_handler.setLevel(logging.INFO)   # - для теста в консоли.


@log
def load_params():
    '''
    Парсер аргументов командной строки, возвращает кортеж из 4 элементов
    адрес сервера, порт, имя пользователя, пароль.
    Выполняет проверку на корректность номера порта.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_password = namespace.password
    if server_port < 1024 or server_port > 65535:
        logger.critical(
            'В качестве порта может быть указано только число в диапазоне от 1024 до 65535.')
        sys.exit(1)

    return server_address, server_port, client_name, client_password


def make_sock_send_msg_get_answer():
    # 192.168.1.109 8081 (при проверке: работает как через терминал, так и
    # через PyCharm)

    server_address, server_port, client_account_name, client_account_password = load_params()
    logger.debug('Аргументы загружены')

    client_app = QApplication(sys.argv)

    database = ClientStorage(client_account_name)

    start_dialog = UsernameDialog()
    # Если имя пользователя не было указано в командной строке то запросим его
    if not client_account_name or not client_account_password:
        client_app.exec_()
        if start_dialog.ok_pressed:
            client_account_name = start_dialog.client_name.text()
            client_account_password = start_dialog.client_passwd.text()
            logger.debug(
                f'USERNAME = {client_account_name}, PASSWORD = {client_account_password}.')
        else:
            exit(0)

    logger.info(
        f'Запущен клиент с парамертами: адрес сервера - {server_address}, '
        f'порт - {server_port}, режим работы - {client_account_name}')

    # Загружаем ключи с файла, если же файла нет, то генерируем новую пару.
    dir_path = os.path.dirname(os.path.realpath(__file__))
    key_file = os.path.join(dir_path, f'{client_account_name}.key')
    if not os.path.exists(key_file):
        keys = RSA.generate(2048, os.urandom)
        with open(key_file, 'wb') as key:
            key.write(keys.export_key())
    else:
        with open(key_file, 'rb') as key:
            keys = RSA.import_key(key.read())

    #   !!!keys.publickey().export_key()
    logger.debug("Ключи успешно загружены.")

    try:
        sock = ClientInteraction(
            server_address,
            server_port,
            client_account_name,
            database,
            client_account_password,
            keys)

        # response = get_response(get_message(sock))
        # logger.info(f'Установлено соединение с сервером. Ответ: {response}')
        # print(f'Установлено соединение с сервером.')

    except (ValueError, json.JSONDecodeError):
        logger.error('Не удалось декодировать сообщение сервера.')
    except (ConnectionRefusedError, ConnectionError) as ex:
        message = QMessageBox()
        message.critical(start_dialog, f'Ошибка сервера: {ex}')
        logger.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}.')
        exit(1)
    sock.setDaemon(True)
    sock.start()

    del start_dialog

    main_window = ClientMainWindow(database, sock, keys)
    main_window.make_connection(sock)
    main_window.setWindowTitle(
        f'Чат Программа alpha release - {client_account_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт
    sock.socket_shutdown()
    sock.join()


if __name__ == '__main__':
    make_sock_send_msg_get_answer()
