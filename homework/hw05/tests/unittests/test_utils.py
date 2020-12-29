import sys
import os
import unittest
import json
# добавляем путь, чтобы видеть внешние папки, например, дойти до common
sys.path.append(os.path.join(os.getcwd(), '../..'))
from common.default_conf import RESPONSE, ERROR, USER, ACCOUNT_NAME, TIME, ACTION, PRESENCE, ENCODING
from common.utils import get_message, send_message


class TestSocket:
    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.encoded_message = None
        self.received_message = None

    def send(self, message_to_send):
        json_test_message = json.dumps(self.test_dict)
        self.encoded_message = json_test_message.encode(ENCODING)
        self.received_message = message_to_send

    def recv(self, max_pkg_len):
        json_test_message = json.dumps(self.test_dict)
        return json_test_message.encode(ENCODING)


class TestUtils(unittest.TestCase):

    test_dict_send = {
        ACTION: PRESENCE,
        TIME: 1233.1233,
        USER: {
            ACCOUNT_NAME: 'Demo_test'
        }
    }

    test_dict_receive_ok = {RESPONSE: 200}
    test_dict_receive_error = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }

    def test_send_message(self):
        test_socket = TestSocket(self.test_dict_send)
        send_message(test_socket, self.test_dict_send)

        # проверка корректной отправки отправляемого сообщения в соответствии с полученным
        self.assertEqual(test_socket.encoded_message, test_socket.received_message)

        # проверяем, если пришел не словарь на отправку
        with self.assertRaises(Exception):
            send_message(test_socket)

    def test_get_message(self):
        test_sock_ok = TestSocket(self.test_dict_receive_ok)
        test_sock_error = TestSocket(self.test_dict_receive_error)

        # проверка корректного получения корректного сообщения
        self.assertEqual(get_message(test_sock_ok), self.test_dict_receive_ok)
        # проверка корректного получения некорректного сообщения
        self.assertEqual(get_message(test_sock_error), self.test_dict_receive_error)


if __name__ == '__main__':
    unittest.main()
