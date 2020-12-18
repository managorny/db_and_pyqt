# from common.default_conf import SERVER_DATEBASE # почему-то не работает
from common.default_conf import *   # взял из примера, помогло, не знаю почему, ответ пока не нашел
import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, INT, VARCHAR, DATETIME, ForeignKey
from sqlalchemy.orm import mapper, sessionmaker


# основной класс для серверной базы
class ServerStorage:
    # создаем шаблоны таблиц (традиционный стиль)
    class Users:
        def __init__(self, username, info, date_create):
            self.id = None
            self.username = username
            self.info = info
            self.date_create = date_create
            self.last_login = datetime.datetime.now()
            self.last_logout = None

    class ActiveUsers:
        def __init__(self, user_id, ip_address, port):
            self.id = None
            self.user_id = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_datetime = datetime.datetime.now()

    class Contacts:
        def __init__(self, owner_id, user_id):
            self.owner_id = owner_id
            self.user_id = user_id

    class LoginHistory:
        def __init__(self, user_id, username, ip_address, port):
            self.id = None
            self.user_id = user_id
            self.username = username
            self.date_time = datetime.datetime.now()
            self.ip_address = ip_address
            self.port = port

    def __init__(self):
        self.database_engine = create_engine(SERVER_DATEBASE, echo=False, pool_recycle=3600)

        self.metadata = MetaData()

        # таблица всех юзеров
        users_table = Table('users', self.metadata,
                            Column('id', INT, primary_key=True),  # INT = Integer
                            Column('username', VARCHAR, unique=True),  # VARCHAR = String
                            Column('date_create', DATETIME),  # DATETIME = DateTime
                            Column('last_login', DATETIME),
                            Column('last_logout', DATETIME)
                            )

        # таблица активных сейчас юзеров
        active_users_table = Table('active_users', self.metadata,
                                   Column('id', INT, primary_key=True),  # INT = Integer
                                   Column('user_id', ForeignKey('users.id'), unique=True),
                                   Column('ip_address', VARCHAR),  # VARCHAR = String
                                   Column('port', VARCHAR),  # VARCHAR = String
                                   Column('login_datetime', DATETIME)  # DATETIME = DateTime
                                   )

        # таблица контактов (юзер-владелец и юзер-контакт, список контактов собираем по юзер-владелец)
        contacts_table = Table('contacts', self.metadata,
                               Column('id', INT, primary_key=True),  # INT = Integer
                               Column('owner_id', ForeignKey('users.id')),
                               Column('user_id', ForeignKey('users.id')))

        # таблица истории входа
        login_history_table = Table('login_history', self.metadata,
                                    Column('id', INT, primary_key=True),  # INT = Integer
                                    Column('user_id', ForeignKey('users.id')),
                                    Column('username', ForeignKey('users.username')),
                                    Column('date_time', DATETIME),  # DATETIME = DateTime
                                    Column('ip_address', VARCHAR),  # VARCHAR = String
                                    Column('port', VARCHAR)  # VARCHAR = String
                                    )

        self.metadata.create_all(self.database_engine)

        # делаем мосты
        mapper(self.Users, users_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.Contacts, contacts_table)
        mapper(self.LoginHistory, login_history_table)

        Session = sessionmaker(bind=self.database_engine)

        self.session = Session()

        # если есть активные юзеры в таблице при запуске сервера, удаляем их
        self.session.query(self.ActiveUsers).delete()

        # коммитим результаты
        self.session.commit()

        # фиксируем вход в базу

    def user_login(self, username, info, ip_address, port):
        query = self.session.query(self.Users).filter_by(username=username)

        # если пользователь существует, обновляем дату последнего входа
        if query.count() > 0:
            user = query.first()
            user.last_login = datetime.datetime.now()

        # если пользователя нет, то создаем его и записываем дату создания
        else:
            date_create = datetime.datetime.now()
            user = self.Users(username, info, date_create)

            self.session.add(user)
            self.session.commit()

        # создаем запись в активных юзерах
        new_active_user = self.ActiveUsers(user.id, ip_address, port)
        self.session.add(new_active_user)

        # создаем запись в истории
        new_user_history = self.LoginHistory(user.id, user.username, ip_address, port)
        self.session.add(new_user_history)

        self.session.commit()

    # фиксируем выход из базы
    def user_logout(self, username):
        # фильтруем уходящего пользователя по его username
        user_logout = self.session.query(self.Users).filter_by(username=username).first()

        # удаляем его из активных юзеров
        self.session.query(self.ActiveUsers).filter_by(user_id=user_logout.id).delete()

        self.session.commit()

    # записываем контакты
    # предполагаем, что запись контактов будет,
    # что тот, кто написал - owner, кому написали - юзер кто в контактах у owner
    def contacts(self, owner_username, contact_username):
        owner = self.session.query(self.Users).filter_by(username=owner_username).first()
        contact = self.session.query(self.Users).filter_by(username=contact_username).first()
        check_owner = self.session.query(self.Contacts).filter_by(owner_id=owner.id)

        # проверяем есть ли уже запись о контакте в списке контактов
        if check_owner.count() > 0:
            for row in check_owner:
                if row.owner_id == owner.id and row.user_id == contact.id:
                    return

        new_contact = self.Contacts(owner.id, contact.id)
        self.session.add(new_contact)

    # смотрим список юзеров
    def select_users(self):
        users_list = self.session.query(self.Users.username, self.Users.date_create)
        return users_list.all()

    # смотрим список активных изеров
    def select_active_users(self):
        active_users_list = self.session.query(
            self.Users.username,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_datetime).join(self.Users)
        return active_users_list.all()

    # смотрим контакты конкретного юзера
    def contacts_list(self, username):
        user = self.session.query(self.Users).filter_by(username=username).first()
        contacts_list = self.session.query(self.Contacts).filter_by(owner_id=user.id)
        contacts_list_names = []
        for row in contacts_list:
            if row.id is not None:
                name = self.session.query(self.Users).filter_by(id=row.user_id).first()
                contacts_list_names.append(name.username)

        return contacts_list_names

    # смотрим историю конкретного юзера
    def login_history_user(self, username=None):
        history_list = self.session.query(
            self.LoginHistory.username,
            self.LoginHistory.date_time,
            self.LoginHistory.ip_address,
            self.LoginHistory.port)

        if username:
            history_list = history_list.filter(self.LoginHistory.username == username)

        return history_list.all()


if __name__ == '__main__':
    test_server_storage = ServerStorage()

    test_server_storage.user_login('user3', 'very good user', '192.168.1.1', '8888')
    test_server_storage.user_login('user4', 'very very good user', '192.168.1.2', '8832')

    test_server_storage.contacts('user1', 'user2')

    print(test_server_storage.select_users())
    print(test_server_storage.select_active_users())
    print(test_server_storage.select_active_users())

    print(test_server_storage.contacts_list('user1'))

    test_server_storage.user_logout('user2')

    print(test_server_storage.select_active_users())

    print(test_server_storage.login_history_user('user2'))
