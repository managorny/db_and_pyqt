import logging

from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QApplication, QLabel, qApp, QComboBox, QPushButton
from PyQt5.QtCore import QEvent, Qt

logger = logging.getLogger('messengerapp_client')


# Стартовый диалог с выбором имени пользователя
class UsernameDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.ok_pressed = False

        self.setWindowTitle('Приветствую!')
        self.setFixedSize(175, 93)

        self.label = QLabel('Введите имя пользователя:', self)
        self.label.move(10, 10)
        self.label.setFixedSize(150, 10)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(154, 20)
        self.client_name.move(10, 30)

        self.btn_ok = QPushButton('Начать', self)
        self.btn_ok.move(10, 60)
        self.btn_ok.clicked.connect(self.click)

        self.btn_cancel = QPushButton('Выход', self)
        self.btn_cancel.move(90, 60)
        self.btn_cancel.clicked.connect(qApp.exit)

        self.label_passwd = QLabel('Введите пароль:', self)
        self.label_passwd.move(10, 55)
        self.label_passwd.setFixedSize(150, 15)

        self.client_passwd = QLineEdit(self)
        self.client_passwd.setFixedSize(154, 20)
        self.client_passwd.move(10, 75)
        self.client_passwd.setEchoMode(QLineEdit.Password)

        self.show()

    # Обработчик кнопки ОК, если поле вводе не пустое, ставим флаг и завершаем
    # приложение.
    def click(self):
        if self.client_name.text():
            self.ok_pressed = True
            qApp.exit()


# Диалог выбора контакта для добавления
class AddContactDialog(QDialog):
    def __init__(self, sock, database):
        super().__init__()
        self.sock = sock
        self.database = database

        self.setFixedSize(350, 120)
        self.setWindowTitle('Выберите контакт для добавления:')
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        self.selector_label = QLabel('Выберите контакт для добавления:', self)
        self.selector_label.setFixedSize(200, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 20)
        self.selector.move(10, 30)

        self.button_refresh = QPushButton('Обновить список', self)
        self.button_refresh.setFixedSize(100, 30)
        self.button_refresh.move(60, 60)

        self.button_ok = QPushButton('Добавить', self)
        self.button_ok.setFixedSize(100, 30)
        self.button_ok.move(230, 20)

        self.button_cancel = QPushButton('Отмена', self)
        self.button_cancel.setFixedSize(100, 30)
        self.button_cancel.move(230, 60)
        self.button_cancel.clicked.connect(self.close)

        # Заполняем список контактов на выбор
        self.select_contacts_update()
        # Назначаем действие на кнопку обновить
        self.button_refresh.clicked.connect(self.update_possible_contacts)

    def select_contacts_update(self):
        self.selector.clear()
        # множества всех контактов и контактов клиента
        contacts_list = set(self.database.get_contacts())
        users_list = set(self.database.get_users())
        # Удаление самого себя из списка пользователей, чтобы нельзя было
        # добавить себя
        users_list.remove(self.sock.username)
        # Добавление списка контактов
        self.selector.addItems(users_list - contacts_list)

    # Обновоение возможных контактов. Обновляет таблицу известных пользователей,
    # затем содержимое предполагаемых контактов
    def update_possible_contacts(self):
        try:
            self.sock.user_list_update()
        except OSError:
            pass
        else:
            logger.debug('Обновление списка пользователей с сервера выполнено')
            self.possible_contacts_update()


# Диалог выбора контакта для удаления
class DeleteContactDialog(QDialog):
    def __init__(self, database):
        super().__init__()
        self.database = database

        self.setFixedSize(350, 120)
        self.setWindowTitle('Выберите контакт для удаления:')
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        self.selector_label = QLabel('Выберите контакт для удаления:', self)
        self.selector_label.setFixedSize(200, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 20)
        self.selector.move(10, 30)

        self.button_ok = QPushButton('Удалить', self)
        self.button_ok.setFixedSize(100, 30)
        self.button_ok.move(230, 20)

        self.button_cancel = QPushButton('Отмена', self)
        self.button_cancel.setFixedSize(100, 30)
        self.button_cancel.move(230, 60)
        self.button_cancel.clicked.connect(self.close)

        # заполнитель контактов для удаления
        self.selector.addItems(sorted(self.database.get_contacts()))


if __name__ == '__main__':
    app = QApplication([])
    username_dialog = UsernameDialog()
    delete_contact_dialog = DeleteContactDialog(None)
    delete_contact_dialog.show()
    app.exec_()
