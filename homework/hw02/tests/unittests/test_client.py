import sys
import os
import unittest
# добавляем путь, чтобы видеть внешние папки, например, дойти до common
sys.path.append(os.path.join(os.getcwd(), '../..'))
from common.default_conf import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    RESPONSE, ERROR
from client import create_presence_message, get_answer


class TestClient(unittest.TestCase):

    def test_ok_message(self):
        test_msg = create_presence_message()
        test_msg[TIME] = '123.123'  # необходимо задать конкретное время, чтобы проверить
        self.assertEqual(test_msg, {ACTION: PRESENCE, TIME: '123.123', USER: {ACCOUNT_NAME: 'Demo'}})

    def test_answer_200(self):
        self.assertEqual(get_answer({RESPONSE: 200}), '200 : OK')

    def test_answer_400(self):
        self.assertEqual(get_answer({RESPONSE: 400, ERROR: 'Bad Request'}), '400 : Bad Request')

    def test_without_response(self):
        with self.assertRaises(ValueError):
            get_answer({})


if __name__ == '__main__':
    unittest.main()
