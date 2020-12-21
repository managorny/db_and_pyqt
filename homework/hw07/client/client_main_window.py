import sys
import logging
from PyQt5.QtWidgets import QMainWindow, qApp, QMessageBox, QApplication, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSlot, QEvent, Qt
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.PublicKey import RSA
import json
import logging
import base64
from client.qdialogs import UsernameDialog, AddContactDialog, DeleteContactDialog
from client.client_ui import Ui_MainClientWindow

logger = logging.getLogger('messengerapp_client')


class ClientMainWindow(QMainWindow):
    def __init__(self, database, sock, keys):
        super().__init__()

        self.database = database
        self.sock = sock

        # объект - дешифорвщик сообщений с предзагруженным ключём
        self.decrypter = PKCS1_OAEP.new(keys)

        # Загрузка окна из дизайнера
        self.ui = Ui_MainClientWindow()
        self.ui.setupUi(self)

        # Кнопка "отправить сообщение"
        self.ui.button_send.clicked.connect(self.send_message)

        # Кнопка "добавить контакт"
        self.ui.button_add_contact.clicked.connect(self.add_contact_window)
        self.ui.menu_add_contact.triggered.connect(self.add_contact_window)

        # Кнопка "удалить контакт"
        self.ui.button_remove_contact.clicked.connect(
            self.delete_contact_window)
        self.ui.menu_del_contact.triggered.connect(self.delete_contact_window)

        # Кнопка "выход"
        self.ui.menu_exit.triggered.connect(qApp.exit)

        self.contacts_model = None
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.current_chat_key = None
        self.encryptor = None
        self.ui.list_messages.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)
        self.ui.list_messages.setWordWrap(True)

        # Двойной клик по листу контактов для чата, отправляется в обработчик
        self.ui.list_contacts.doubleClicked.connect(self.select_active_user)

        self.clients_list_update()
        self.set_disabled_input()
        self.show()

    # Деактивация поля ввода пока не выбран получатель
    def set_disabled_input(self):
        self.ui.label_new_message.setText(
            'Для выбора получателя дважды кликните на нем в окне контактов.')
        self.ui.text_message.clear()
        if self.history_model:
            self.history_model.clear()

        self.ui.button_clear.setDisabled(True)
        self.ui.button_send.setDisabled(True)
        self.ui.text_message.setDisabled(True)

    # Функция обработчик двойного клика по контакту
    def select_active_user(self):
        # Выбранный пользователем (даблклик) находится в выделеном элементе в
        # QListView
        self.current_chat = self.ui.list_contacts.currentIndex().data()
        # вызываем основную функцию
        self.set_active_user()

    # Функция устанавливающяя активного собеседника
    def set_active_user(self):
        """Метод активации чата с собеседником."""
        # Запрашиваем публичный ключ пользователя и создаём объект шифрования
        try:
            self.current_chat_key = self.sock.key_request(
                self.current_chat)
            logger.debug(f'Загружен открытый ключ для {self.current_chat}')
            if self.current_chat_key:
                self.encryptor = PKCS1_OAEP.new(
                    RSA.import_key(self.current_chat_key))
        except (OSError, json.JSONDecodeError):
            self.current_chat_key = None
            self.encryptor = None
            logger.debug(f'Не удалось получить ключ для {self.current_chat}')

        # Если ключа нет то ошибка, что не удалось начать чат с пользователем
        if not self.current_chat_key:
            self.messages.warning(
                self, 'Ошибка', 'Для выбранного пользователя нет ключа шифрования.')
            return

        # Ставим надпись и активируем кнопки
        self.ui.label_new_message.setText(
            f'Введите сообщенние для {self.current_chat}:')
        self.ui.button_clear.setDisabled(False)
        self.ui.button_send.setDisabled(False)
        self.ui.text_message.setDisabled(False)

        # Заполняем окно историей сообщений по требуемому пользователю.
        self.history_list_update()

    # Функция обновляющяя список контактов
    def clients_list_update(self):
        contacts_list = self.database.get_contacts()
        self.contacts_model = QStandardItemModel()
        for i in sorted(contacts_list):
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    # Заполнение истории сообщений
    def history_list_update(self):
        # Получаем историю сортированную по дате
        message_list = sorted(
            self.database.get_history(
                self.current_chat),
            key=lambda new_item: new_item[3])
        # Если модель не создана, создаем
        if not self.history_model:
            self.history_model = QStandardItemModel()
            self.ui.list_messages.setModel(self.history_model)
        # Очистим от старых записей
        self.history_model.clear()
        # Берём не более 50 последних записей
        length = len(message_list)
        start_index = 0
        if length > 50:
            start_index = length - 50
        # Заполнение модели записями, так-же стоит разделить входящие и исходящие выравниванием и разным фоном.
        # Записи в обратном порядке, поэтому выбираем их с конца и не более 50
        for i in range(start_index, length):
            item = message_list[i]
            if item[1] == 'in':
                mess = QStandardItem(
                    f'Входящее от {item[3].replace(microsecond=0)}:\n {item[2]}')
                mess.setEditable(False)
                mess.setBackground(QBrush(QColor(255, 213, 213)))
                mess.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(mess)
            else:
                mess = QStandardItem(
                    f'Исходящее от {item[3].replace(microsecond=0)}:\n {item[2]}')
                mess.setEditable(False)
                mess.setTextAlignment(Qt.AlignRight)
                mess.setBackground(QBrush(QColor(204, 255, 204)))
                self.history_model.appendRow(mess)
        self.ui.list_messages.scrollToBottom()

    # Функция добавления контакта
    def add_contact_window(self):
        global select_dialog
        select_dialog = AddContactDialog(self.sock, self.database)
        select_dialog.button_ok.clicked.connect(
            lambda: self.add_contact_action(select_dialog))
        select_dialog.show()

    # Функция - обработчик добавления, сообщает серверу, обновляет таблицу и
    # список контактов
    def add_contact_action(self, item):
        new_contact = item.selector.currentText()
        self.add_contact(new_contact)
        item.close()

    # Функция добавляющяя контакт в базы
    def add_contact(self, new_contact):
        try:
            self.sock.add_contact(new_contact)
        except Exception as ex:
            self.messages.critical(self, 'Ошибка сервера', ex.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(
                    self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.database.add_contact(new_contact)
            new_contact = QStandardItem(new_contact)
            new_contact.setEditable(False)
            self.contacts_model.appendRow(new_contact)
            logger.info(f'Успешно добавлен контакт {new_contact}')
            self.messages.information(
                self, 'Успех', 'Контакт успешно добавлен.')

    # Функция удаления контакта
    def delete_contact_window(self):
        global remove_dialog
        remove_dialog = DeleteContactDialog(self.database)
        remove_dialog.button_ok.clicked.connect(
            lambda: self.delete_contact(remove_dialog))
        remove_dialog.show()

    # Функция обработчик удаления контакта, сообщает на сервер, обновляет
    # таблицу контактов
    def delete_contact(self, item):
        selected = item.selector.currentText()
        try:
            self.sock.remove_contact(selected)
        except Exception as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(
                    self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.database.del_contact(selected)
            self.clients_list_update()
            logger.info(f'Успешно удалён контакт {selected}')
            self.messages.information(self, 'Успех', 'Контакт успешно удалён.')
            item.close()
            # Если удалён активный пользователь, то деактивируем поля ввода.
            if selected == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    # Функция отправки собщения пользователю.
    def send_message(self):
        # Текст в поле, проверяем что поле не пустое затем забирается сообщение
        # и поле очищается
        message_text = self.ui.text_message.toPlainText()
        self.ui.text_message.clear()
        if not message_text:
            return
        # Шифруем сообщение ключом получателя и упаковываем в base64.
        message_text_encrypted = self.encryptor.encrypt(
            message_text.encode('utf8'))
        message_text_encrypted_base64 = base64.b64encode(
            message_text_encrypted)
        try:
            self.sock.send_message(
                self.current_chat,
                message_text_encrypted_base64.decode('ascii'))
            pass
        except Exception as err:
            self.messages.critical(self, 'Ошибка', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(
                    self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        except (ConnectionResetError, ConnectionAbortedError):
            self.messages.critical(
                self, 'Ошибка', 'Потеряно соединение с сервером!')
            self.close()
        else:
            self.database.save_message(self.current_chat, message_text)
            logger.debug(
                f'Отправлено сообщение для {self.current_chat}: {message_text}')
            self.history_list_update()

    # Слот приема нового сообщений
    @pyqtSlot(str)
    def message(self, message):
        """
        Слот обработчик поступаемых сообщений, выполняет дешифровку
        поступаемых сообщений и их сохранение в истории сообщений.
        Запрашивает пользователя если пришло сообщение не от текущего
        собеседника. При необходимости меняет собеседника.
        """
        # Получаем строку байтов
        encrypted_message = base64.b64decode(message[MESSAGE_CLIENT])
        # Декодируем строку, при ошибке выдаём сообщение и завершаем функцию
        try:
            decrypted_message = self.decrypter.decrypt(encrypted_message)
        except (ValueError, TypeError):
            self.messages.warning(
                self, 'Ошибка', 'Не удалось декодировать сообщение.')
            return
        # Сохраняем сообщение в базу и обновляем историю сообщений или
        # открываем новый чат.
        decrypted_message = decrypted_message.decode('utf-8')
        to = decrypted_message[TO][ACCOUNT_NAME]

        self.database.save_message(to, self.current_chat, decrypted_message)

        sender = message[FROM][ACCOUNT_NAME]
        if sender == self.current_chat:
            self.history_list_update()
        else:
            # Проверим есть ли такой пользователь в контактах:
            if self.database.check_contact(sender):
                # Если есть, спрашиваем о желании открыть с ним чат и открываем
                # при Yes
                if self.messages.question(
                        self,
                        f'Новое сообщение\n',
                        f'Получено новое сообщение от {sender}, открыть чат с ним?',
                        QMessageBox.Yes,
                        QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    self.set_active_user()
            else:
                print('NO')
                # Если пользователя нет, то спрашиваем хотим ли добавить юзера
                # в контакты.
                if self.messages.question(
                        self,
                        'Новое сообщение\n',
                        f'Получено новое сообщение от {sender}.\n'
                        f'Данного пользователя нет в вашем списке контактов.\n'
                        f'Добавить в контакты и открыть чат с ним?',
                        QMessageBox.Yes,
                        QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(sender)
                    self.current_chat = sender
                    self.database.save_message(
                        to, self.current_chat, decrypted_message)
                    self.set_active_user()

    @pyqtSlot()
    def connection_lost(self):
        self.messages.warning(
            self,
            'Сбой соединения',
            'Потеряно соединение с сервером. ')
        self.close()

    @pyqtSlot()
    def sig_205(self):
        """
        Слот выполняющий обновление баз данных по команде сервера.
        """
        if self.current_chat and not self.database.check_user(
                self.current_chat):
            self.messages.warning(
                self, 'К сожалению собеседник был удален с сервера.')
            self.set_disabled_input()
            self.current_chat = None
        self.clients_list_update()

    def make_connection(self, trans_obj):
        trans_obj.new_message.connect(self.message)
        trans_obj.connection_lost.connect(self.connection_lost)
        trans_obj.message_205.connect(self.sig_205)
