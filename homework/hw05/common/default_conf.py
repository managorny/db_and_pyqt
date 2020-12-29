DEFAULT_PORT = 7777
DEFAULT_IP_ADDRESS = 'localhost'
MAX_CONNECTIONS = 5
MAX_PACKAGE_LENGTH = 2048
ENCODING = 'utf-8'
SERVER_DATABASE = 'sqlite:///server_db.db3'

# Прококол JIM основные ключи:
ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'account_name'
PASSWORD = 'password'
FROM = 'from'
TO = 'to'
MESSAGE = 'message'
MESSAGE_CLIENT = 'message_text'

# Прочие ключи, используемые в протоколе
PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
ALERT = 'alert'
TYPE = 'type'
ROOM = 'room'
INFO = 'info'
ADD_CONTACT = 'add_contact'
REMOVE_CONTACT = 'remove_contact'
GET_CONTACTS = 'get_contacts'
CONTACT = 'contact'
USERS_LIST = 'users_list'
