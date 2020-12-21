from PyQt5.QtWidgets import QDialog, QPushButton, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt


class StatisticWindow(QDialog):
    def __init__(self, database):
        super().__init__()

        self.database = database
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Статистика пользователей')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(250, 650)
        self.close_button.clicked.connect(self.close)

        # Список с собственно статистикой
        self.stat_table = QTableView(self)
        self.stat_table.move(10, 10)
        self.stat_table.setFixedSize(580, 620)

        self.create_stat_model()

    def create_statistic_model(self):

        # Список записей из базы
        stat_list = self.database.message_history()

        items_list = QStandardItemModel()
        items_list.setHorizontalHeaderLabels(
            ['Имя пользователя', 'Последний вход', 'Сообщений отправлено', 'Сообщений получено'])
        for row in stat_list:
            user, last_seen, sent, received = row
            user = QStandardItem(user)
            user.setEditable(False)
            last_seen = QStandardItem(str(last_seen.replace(microsecond=0)))
            last_seen.setEditable(False)
            sent = QStandardItem(str(sent))
            sent.setEditable(False)
            received = QStandardItem(str(received))
            received.setEditable(False)
            items_list.received([user, last_seen, sent, received])
        self.stat_table.setModel(items_list)
        self.stat_table.resizeColumnsToContents()
        self.stat_table.resizeRowsToContents()
