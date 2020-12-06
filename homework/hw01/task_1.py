"""
1. Написать функцию host_ping(), в которой с помощью утилиты ping будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять их доступность с выводом соответствующего сообщения
(«Узел доступен», «Узел недоступен»). При этом ip-адрес сетевого узла должен создаваться с помощью функции ip_address().
"""

from subprocess import Popen, PIPE
from ipaddress import ip_address
from tabulate import tabulate
import socket


# Mac OS
def host_ping(addresses_list, timeout, count):
    res = {'Доступные узлы': [], 'Недоступные узлы': []}
    for address in addresses_list:
        try:
            address = ip_address(address)
        except ValueError:
            try:
                # address = socket.getaddrinfo(address, 'https')
                address = socket.gethostbyname(address)
            except Exception:
                print(f'Bad address - {address}')
                continue
        operation = Popen(['ping', f'-W {timeout}', f'-c {count}', f'{address}'], shell=False, stdout=PIPE)
        operation.wait()
        if operation.returncode == 0:
            print(f'Узел {address} доступен')
        else:
            print(f'Узел {address} недоступен')
        # if operation.returncode == 0:
        #     res['Доступные узлы'].append(str(address))
        # else:
        #     res['Недоступные узлы'].append(str(address))
    return res


if __name__ == '__main__':
    list_of_addresses = ['yandex.ru', 'sdfsf', '188.226.68.21', '188.226.68.20', '188.226.68.19', '188.226.68.18']
    host_ping(list_of_addresses, 500, 1)
    # result = host_ping(list_of_addresses, 500, 1)
    # columns = []
    # for key in result:
    #     columns.append(key)
    # print(tabulate(result, headers=columns))
