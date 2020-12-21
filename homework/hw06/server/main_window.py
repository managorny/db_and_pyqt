from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, QTableView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QTimer
from server.statistic_window import StatisticWindow
from server.config_window import ConfigWindow
from server.new_user_window import RegisterUser
from server.remove_user_window import RemoveUserDialog


class MainWindow(QMainWindow):

    def __init__(self, database, server, config):
        super().__init__()

        self.database = database

        # thread с сервером
        self.server = server

        self.config = config

        # Кнопка обновить список пользователей
        self.refresh_button = QAction('Обновить список', self)

        # Кнопка регистрации пользователя
        self.register_btn = QAction('Регистрация пользователя', self)

        # Кнопка удаления пользователя
        self.remove_btn = QAction('Удаление пользователя', self)

        # Кнопка вывести историю сообщений
        self.show_history_button = QAction('История пользователей', self)

        # Кнопка настроек сервера
        self.config_btn = QAction('Настройки сервера', self)

        # Ярлык выхода
        self.exitAction = QAction('Выход', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.triggered.connect(qApp.quit)

        self.statusBar()
        self.statusBar().showMessage('Server Working')

        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(self.exitAction)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_btn)
        self.toolbar.addAction(self.register_btn)
        self.toolbar.addAction(self.remove_btn)

        # Настройка размеров основного окна
        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging Server alpha release')

        self.label = QLabel('Список подключённых пользователей:', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 25)

        # Окно со списком подключённых пользователей
        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 45)
        self.active_clients_table.setFixedSize(780, 400)

        # Таймер, обновляющий список клиентов 1 раз в секунду
        self.timer = QTimer()
        self.timer.timeout.connect(self.create_users_model)
        self.timer.start(1000)

        # Связь кнопок с процедурами
        self.refresh_button.triggered.connect(self.create_users_model)
        self.show_history_button.triggered.connect(self.show_statistics)
        self.config_btn.triggered.connect(self.server_config)
        self.register_btn.triggered.connect(self.reg_user)
        self.remove_btn.triggered.connect(self.rem_user)

        # Отображение окна
        self.show()

    def create_active_users_model(self):
        """
        Заполнение таблицы активных пользователей
        """
        list_active_users = self.database.select_active_users()
        items_list = QStandardItemModel()
        items_list.setHorizontalHeaderLabels(
            ['Имя Клиента', 'IP Адрес', 'Порт', 'Время подключения'])
        for row in list_active_users:
            user, ip, port, time = row
            user = QStandardItem(user)
            user.setEditable(False)
            ip = QStandardItem(ip)
            ip.setEditable(False)
            port = QStandardItem(str(port))
            port.setEditable(False)

            time = QStandardItem(str(time.replace(microsecond=0)))
            time.setEditable(False)
            items_list.appendRow([user, ip, port, time])
        self.active_clients_table.setModel(items_list)
        self.active_clients_table.resizeColumnsToContents()
        self.active_clients_table.resizeRowsToContents()

    def user_registration(self):
        """
        Создание и отображение окна для регистрации пользователя
        """
        global reg_window
        reg_window = RegisterUser(self.database, self.server)
        reg_window.show()

    def rem_user(self):
        """
        Создание и отображение окна для удаления пользователя
        """
        global rem_window
        rem_window = RemoveUserDialog(self.database, self.server)
        rem_window.show()

    def show_statistics(self):
        """
        Создание и отображение окна со статистикой
        """
        global stat_window
        stat_window = StatisticWindow(self.database)
        stat_window.show()

    def server_config(self):
        """
        Создание и отображение окна с настройками сервера
        """
        global config_window
        # Создание окна и заполнение в него текущие параметры
        config_window = ConfigWindow(self.config)
