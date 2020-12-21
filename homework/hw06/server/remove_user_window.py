from PyQt5.QtWidgets import QDialog, QLabel, QComboBox, QPushButton, QApplication
from PyQt5.QtCore import Qt


class RemoveUserDialog(QDialog):
    def __init__(self, database, server):
        super().__init__()
        self.database = database
        self.server = server

        self.setFixedSize(350, 120)
        self.setWindowTitle('Удаление пользователя')
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        self.selector_label = QLabel(
            'Выберите пользователя для удаления:', self)
        self.selector_label.setFixedSize(200, 20)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(200, 20)
        self.selector.move(10, 30)

        self.button_ok = QPushButton('Удалить', self)
        self.button_ok.setFixedSize(100, 30)
        self.button_ok.move(230, 20)
        self.button_ok.clicked.connect(self.remove_user)

        self.button_cancel = QPushButton('Отмена', self)
        self.button_cancel.setFixedSize(100, 30)
        self.button_cancel.move(230, 60)
        self.button_cancel.clicked.connect(self.close)

        self.add_all_users()

    def add_all_users(self):
        self.selector.addItems([item[0] for item in self.database.select_users()])

    def remove_user(self):
        self.database.remove_user(self.selector.currentText())
        if self.selector.currentText() in self.server.account_names_list:
            sock = self.server.account_names_list[self.selector.currentText()]
            del self.server.account_names_list[self.selector.currentText()]
            self.server.remove_client(sock)
        # Рассылаем клиентам сообщение о необходимости обновить справочники
        self.server.service_update_lists()
        self.close()
