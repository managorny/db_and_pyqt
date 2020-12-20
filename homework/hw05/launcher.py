import time
import os
from subprocess import Popen

text_for_choice = """
1 - запуск сервера
2 - остановка сервера
3 - запуск 3 юзеров
4 - остановка клиентов
5 - остановить все и выйти
Выберите действие: \n"""

clients = []
server = ''
path_to_file = os.path.dirname(__file__)
path_to_script_server = os.path.join(path_to_file, "server.py")
path_to_script_client = os.path.join(path_to_file, "client.py")

while True:
    choice = input(text_for_choice)

    if choice == '1':
        print("Запустили сервер")
        server = Popen(
            f'osascript -e \'tell application "Terminal" to do'
            f' script "python3 {path_to_script_server} -p 8081 -address 192.168.1.109"\'', shell=True)
    elif choice == '2':
        print("Убили сервер")
        server.kill()
    elif choice == '3':
        print("Запустили клиенты")
        clients.append(
            Popen(
                f'osascript -e \'tell application "Terminal" to do'
                f' script "python3 {path_to_script_client} 192.168.1.109 8081 -n user1"\'',
                shell=True))
        clients.append(
            Popen(
                f'osascript -e \'tell application "Terminal" to do'
                f' script "python3 {path_to_script_client} 192.168.1.109 8081 -n user2"\'',
                shell=True))
        clients.append(
            Popen(
                f'osascript -e \'tell application "Terminal" to do'
                f' script "python3 {path_to_script_client} 192.168.1.109 8081 -n user3"\'',
                shell=True))
    elif choice == '4':
        for i in range(len(clients)):
            print(clients[i])
            clients[i].kill()
    elif choice == '5':
        for i in range(len(clients)):
            clients[i].kill()
        server.kill()
        break
