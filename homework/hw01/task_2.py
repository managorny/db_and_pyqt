"""
2. Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
"""
from subprocess import Popen, PIPE
from ipaddress import ip_address
import socket


# Mac OS
def host_range_ping(address, my_range, timeout, count):
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
    for new_last_oktet in range(last_oktet, last_oktet + my_range + 1):
        address = str(address).split('.')[:-1]
        address.append(str(new_last_oktet))
        address = ip_address('.'.join(address))
        operation = Popen(['ping', f'-W {timeout}', f'-c {count}', f'{address}'], shell=False, stdout=PIPE)
        operation.wait()
        if operation.returncode == 0:
            print(f'Узел {address} доступен')
        else:
            print(f'Узел {address} недоступен')
    return


if __name__ == '__main__':
    my_address = 'yandex.ru'
    host_range_ping(my_address, 5, 500, 1) # ip, range, timeout, count requests
