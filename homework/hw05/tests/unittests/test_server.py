import sys
import os
import unittest
# добавляем путь, чтобы видеть внешние папки, например, дойти до common
sys.path.append(os.path.join(os.getcwd(), '../..'))
from common.default_conf import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    RESPONSE, ERROR
from server import process_client_message


class TestServer(unittest.TestCase):
    # тестовые данные
    ok_dict = {RESPONSE: 200}
    error_dict = {
        RESPONSE: 400,
        ERROR: 'Bad Request'
    }

    def test_ok_message(self):
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: '123.123', USER: {ACCOUNT_NAME: 'Demo'}}), self.ok_dict)

    def test_without_action(self):
        self.assertEqual(process_client_message(
            {TIME: '123.123', USER: {ACCOUNT_NAME: 'Demo'}}), self.error_dict)

    def test_wrong_action(self):
        self.assertEqual(process_client_message(
            {ACTION: 'test_not_ok_action', TIME: '123.123', USER: {ACCOUNT_NAME: 'Demo'}}), self.error_dict)

    def test_without_time(self):
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Demo'}}), self.error_dict)

    def test_without_user(self):
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: '123.123'}), self.error_dict)

    def test_not_ok_user(self):
        self.assertEqual(process_client_message(
            {ACTION: PRESENCE, TIME: '123.123', USER: {ACCOUNT_NAME: 'TestNotOkUser'}}), self.error_dict)


if __name__ == '__main__':
    unittest.main()
