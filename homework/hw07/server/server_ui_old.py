import sys
import os
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QLabel, QTableView, QDialog, QPushButton, \
    QLineEdit, QFileDialog, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDesktopWidget


# создание базовой таблицы для отображения в окне интерфейса
def create_users_model(server_database):
    list_active_users = server_database.select_active_users()
    list_td = QStandardItemModel()
    list_td.setHorizontalHeaderLabels(
        ['Имя пользователя', 'IP Адрес', 'Порт', 'Время подключения'])
    for row in list_active_users:
        username, ip, port, time = row
        username = QStandardItem(username)
        username.setEditable(False)
        ip = QStandardItem(ip)
        ip.setEditable(False)
        # переведем порт в строку для надежности
        port = QStandardItem(str(port))
        port.setEditable(False)
        # microsecond=0 - убирает микросекунды
        time = QStandardItem(str(time.replace(microsecond=0)))
        time.setEditable(False)
        list_td.appendRow([username, ip, port, time])
    return list_td


# таблица для истории
def create_history_model(database):
    # Список записей из базы
    hist_list = database.get_message_count_history()

    # Объект модели данных:
    list_td = QStandardItemModel()
    list_td.setHorizontalHeaderLabels(
        ['Имя пользователя', 'Последний вход', 'Сообщений отправлено', 'Сообщений получено'])
    for row in hist_list:
        username, last_login, sent, received = row
        username = QStandardItem(username)
        username.setEditable(False)
        last_login = QStandardItem(str(last_login.replace(microsecond=0)))
        last_login.setEditable(False)
        sent = QStandardItem(str(sent))
        sent.setEditable(False)
        received = QStandardItem(str(received))
        received.setEditable(False)
        list_td.appendRow([username, last_login, sent, received])
    return list_td


# Класс основного окна
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Кнопка выхода
        exitAction = QAction('Выход', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(qApp.quit)

        # Кнопка обновить список пользователей
        self.refresh_button = QAction('Обновить список', self)

        # Кнопка настроек сервера
        self.config_button = QAction('Настройки сервера', self)

        # Кнопка вывести историю сообщений
        self.show_history_button = QAction('История пользователей', self)

        # Статусбар
        # dock widget
        self.statusBar()

        # Тулбар
        self.toolbar = self.addToolBar('MainBar')
        self.toolbar.addAction(exitAction)
        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_button)
        self.toolbar.addAction(self.config_btn)

        # Настройки размеров и позиции основного окна
        # Пока делаем фикс размеры (но можно и динамические)
        self.setFixedSize(800, 600)
        self.setWindowTitle('Messaging Server alpha release')

        # Надпись о том, что ниже список подключённых пользователей
        self.label = QLabel('Список подключённых пользователей:', self)
        self.label.setFixedSize(240, 15)
        self.label.move(10, 25)

        # Окно со списком подключённых пользователей
        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 45)
        self.active_clients_table.setFixedSize(780, 400)

        # Последним параметром отображаем окно.
        self.show()

        # центрируем окно
        screen_center = QDesktopWidget().screenGeometry()
        x = int((screen_center.width() - self.width()) / 2)
        y = int((screen_center.height() - self.height()) / 2)
        self.move(x, y)


# Класс окна с историей пользователей
class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Настройки окна:
        self.setWindowTitle('Статистика пользователей')
        self.setFixedSize(600, 700)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Кнапка закрытия окна
        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(250, 650)
        self.close_button.clicked.connect(self.close)

        # Лист с собственно историей
        self.history_table = QTableView(self)
        self.history_table.move(10, 10)
        self.history_table.setFixedSize(580, 620)

        self.show()

        # центрируем окно
        screen_center = QDesktopWidget().screenGeometry()
        x = int((screen_center.width() - self.width()) / 2)
        y = int((screen_center.height() - self.height()) / 2)
        self.move(x, y)


# Класс окна настроек
class ConfigWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Настройки окна
        self.setFixedSize(365, 260)
        self.setWindowTitle('Настройки сервера')

        # Надпись о файле базы данных:
        self.db_path_label = QLabel('Путь до файла базы данных: ', self)
        self.db_path_label.move(10, 10)
        self.db_path_label.setFixedSize(240, 15)

        # Строка с путём базы
        self.db_path = QLineEdit(self)
        self.db_path.setFixedSize(250, 20)
        self.db_path.move(10, 30)
        self.db_path.setReadOnly(True)

        # Кнопка выбора пути
        self.db_path_select = QPushButton('Обзор...', self)
        self.db_path_select.move(275, 28)

        # Функция обработчик открытия окна выбора папки
        def open_file_dialog():
            global dialog
            dialog = QFileDialog(self)
            path = dialog.getExistingDirectory()
            path = path.replace('/', '\\')
            self.db_path.insert(path)

        self.db_path_select.clicked.connect(open_file_dialog)

        # Метка с именем поля файла базы данных
        self.db_file_label = QLabel('Имя файла базы данных: ', self)
        self.db_file_label.move(10, 68)
        self.db_file_label.setFixedSize(180, 15)

        # Поле для ввода имени файла
        self.db_file = QLineEdit(self)
        self.db_file.move(200, 66)
        self.db_file.setFixedSize(150, 20)

        # Метка с номером порта
        self.port_label = QLabel('Номер порта для соединений:', self)
        self.port_label.move(10, 108)
        self.port_label.setFixedSize(180, 15)

        # Поле для ввода номера порта
        self.port = QLineEdit(self)
        self.port.move(200, 108)
        self.port.setFixedSize(150, 20)

        # Метка с адресом для соединений
        self.ip_label = QLabel('С какого IP принимаем соединения:', self)
        self.ip_label.move(10, 148)
        self.ip_label.setFixedSize(180, 15)

        # Метка с напоминанием о пустом поле
        self.ip_label_note = QLabel(
            ' оставьте это поле пустым, чтобы\n принимать соединения с любых адресов.',
            self)
        self.ip_label_note.move(10, 168)
        self.ip_label_note.setFixedSize(500, 30)

        # Поле для ввода ip
        self.ip = QLineEdit(self)
        self.ip.move(200, 148)
        self.ip.setFixedSize(150, 20)

        # Кнопка сохранения настроек
        self.save_button = QPushButton('Сохранить', self)
        self.save_button.move(190, 220)

        # Кнапка закрытия окна
        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(275, 220)
        self.close_button.clicked.connect(self.close)

        self.show()

        # центрируем окно
        screen_center = QDesktopWidget().screenGeometry()
        x = int((screen_center.width() - self.width()) / 2)
        y = int((screen_center.height() - self.height()) / 2)
        self.move(x, y)


if __name__ == '__main__':
    # app = QApplication(sys.argv)
    # ex = MainWindow()
    # ex.statusBar().showMessage('Test Statusbar Message')
    # test_list = QStandardItemModel(ex)
    # test_list.setHorizontalHeaderLabels(['Имя Клиента', 'IP Адрес', 'Порт', 'Время подключения'])
    # test_list.appendRow([QStandardItem('1'), QStandardItem('2'), QStandardItem('3')])
    # test_list.appendRow([QStandardItem('4'), QStandardItem('5'), QStandardItem('6')])
    # ex.active_clients_table.setModel(test_list)
    # ex.active_clients_table.resizeColumnsToContents()
    # print('JKJKJK')
    # app.exec_()
    # print('END')
    app = QApplication(sys.argv)
    message = QMessageBox
    dial = ConfigWindow()

    app.exec_()
