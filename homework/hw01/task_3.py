"""
Написать функцию host_range_ping_tab(), возможности которой основаны на функции из примера 2.
Но в данном случае результат должен быть итоговым по всем ip-адресам, представленным в табличном формате
(использовать модуль tabulate). Таблица должна состоять из двух колонок
"""
from subprocess import Popen, PIPE
from ipaddress import ip_address
from tabulate import tabulate
import socket


# Mac OS
def host_range_ping_tab(address, my_range, timeout, count):
    try:
        address = ip_address(address)
    except ValueError:
        try:
            # address = socket.getaddrinfo(address, 'https')
            address = socket.gethostbyname(address)
        except Exception as ex:
            return print(f'Это не ip или домен')

    last_oktet = str(address).split('.')[-1]
    if not int(last_oktet):
        return print(f'Это не ip')
    else:
        last_oktet = int(last_oktet)
    res = {'Доступные узлы': [], 'Недоступные узлы': []}
    for new_last_oktet in range(last_oktet, last_oktet + my_range + 1):
        address = str(address).split('.')[:-1]
        address.append(str(new_last_oktet))
        address = ip_address('.'.join(address))
        operation = Popen(['ping', f'-W {timeout}', f'-c {count}', f'{address}'], shell=False, stdout=PIPE)
        operation.wait()
        if operation.returncode == 0:
            res['Доступные узлы'].append(str(address))
        else:
            res['Недоступные узлы'].append(str(address))
    return res


if __name__ == '__main__':
    my_address = 'yandex.ru'
    result = host_range_ping_tab(my_address, 5, 500, 1) # ip, range, timeout, count requests
    columns = []
    for key in result:
        columns.append(key)
    print(tabulate(result, headers=columns))
