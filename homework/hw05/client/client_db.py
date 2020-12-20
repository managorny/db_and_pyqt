import sys
sys.path.append('../')
from common.default_conf import *  # взял из примера, помогло, не знаю почему, ответ пока не нашел
import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, INT, VARCHAR, DATETIME, TEXT, ForeignKey
from sqlalchemy.orm import mapper, sessionmaker


class ClientStorage:
    class KnownUsers:
        def __init__(self, username):
            self.id = None
            self.username = username

    class MessageHistory:
        def __init__(self, from_user, to_user, message):
            self.id = None
            self.from_user = from_user
            self.to_user = to_user
            self.message = message
            self.date = datetime.datetime.now()

    class Contacts:
        def __init__(self, username):
            self.id = None
            self.username = username

    def __init__(self, username):
        self.database_engine = create_engine(f'sqlite:///client_{username}_db.db3', echo=False, pool_recycle=3600)

        self.metadata = MetaData()

        known_users_table = Table('known_users', self.metadata,
                                  Column('id', INT, primary_key=True),
                                  Column('username', VARCHAR)
                                  )

        message_history_table = Table('message_history', self.metadata,
                                      Column('id', INT, primary_key=True),
                                      Column('from_user', VARCHAR),
                                      Column('to_user', VARCHAR),
                                      Column('message', TEXT),
                                      Column('date', DATETIME)
                                      )

        contacts_table = Table('contacts', self.metadata,
                               Column('id', INT, primary_key=True),
                               Column('username', VARCHAR, unique=True)
                               )

        self.metadata.create_all(self.database_engine)

        # делаем мосты
        mapper(self.KnownUsers, known_users_table)
        mapper(self.MessageHistory, message_history_table)
        mapper(self.Contacts, contacts_table)

        Session = sessionmaker(bind=self.database_engine)

        self.session = Session()

        # Контакты обновляются при каждом запуске (подтягиваются с сервера), для этого надо очищать перед запуском
        self.session.query(self.Contacts).delete()

        # коммитим результаты
        self.session.commit()

    def add_contact(self, contact):
        if not self.session.query(self.Contacts).filter_by(username=contact).count():
            new_contact = self.Contacts(contact)
            self.session.add(new_contact)
            self.session.commit()

    def remove_contact(self, contact):
        self.session.query(self.Contacts).filter_by(username=contact).delete()

        self.session.commit()

    # список пользователей подтягивается с сервера, поэтому таблица очищается перед заполнением
    def add_known_users(self, users_list):
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            new_user = self.KnownUsers(user)
            self.session.add(new_user)
        self.session.commit()

    # сохранение сообщений при отправке и получении
    def save_message(self, from_user, to_user, message):
        new_message = self.MessageHistory(from_user, to_user, message)
        self.session.add(new_message)
        self.session.commit()

    def get_known_users(self):
        # known_users_list = self.session.query(self.KnownUsers.username).all()
        # for user in known_users_list:
        #     print(user[0])
        return [user[0] for user in self.session.query(self.KnownUsers.username).all()]

    def get_contacts(self):
        # contacts = self.session.query(self.Contacts.username).all()
        # for contact in contacts:
        #     print(contact[0])
        return [contact[0] for contact in self.session.query(self.Contacts.username).all()]

    #  проверка наличия пользователя в уже известных
    def check_user(self, username):
        if self.session.query(self.KnownUsers).filter_by(username=username).count():
            return True
        else:
            return False

    # проверка наличия пользователя в контактах
    def check_contact(self, contact):
        if self.session.query(self.Contacts).filter_by(username=contact).count():
            return True
        else:
            return False

    # получение списка истории сообщений
    def get_message_history(self, from_user=None, to_user=None):
        messages = self.session.query(self.MessageHistory)
        if from_user:
            messages = messages.filter_by(from_user=from_user)
        if to_user:
            messages = messages.filter_by(to_user=to_user)
        for message in messages:
            # print(f'{message.from_user} - {message.to_user} - {message.message} - {message.date}')
            return [(history_row.from_user, history_row.to_user, history_row.message, history_row.date)
                    for history_row in messages.all()]


if __name__ == '__main__':
    test_client_storage = ClientStorage('user1')

    for i in ['user2', 'user3', 'user4']:
        test_client_storage.add_contact(i)

    test_client_storage.add_known_users(['user1', 'user2', 'user3', 'user4', 'user5'])
    # test_client_storage.save_message('user1', 'user2', f'Тестовое сообщение от {datetime.datetime.now()}!')
    # test_client_storage.save_message('user2', 'user1', f'Тестовое сообщение от {datetime.datetime.now()}!')
    # test_client_storage.save_message('user2', 'user3', f'Тестовое сообщение от {datetime.datetime.now()}!')

    print(f'Известные юзеры {test_client_storage.get_known_users()}')
    print(f'Контакты {test_client_storage.get_contacts()}')
    print(test_client_storage.check_user('user1'))
    print(test_client_storage.check_user('user8'))

    print('user1')
    test_client_storage.get_message_history('user1')
    print('from_user=user2')
    test_client_storage.get_message_history(from_user='user2')
    print('to_user=user3')
    test_client_storage.get_message_history(to_user='user3')

    test_client_storage.remove_contact('user3')
    print(test_client_storage.get_contacts())
