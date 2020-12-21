import dis


class ClientVerifier(type):

    def __init__(cls, usual_class, bases, methods):
        super().__init__(usual_class, bases, methods)

        methods_list = []

        for func in methods:
            # print(func)
            try:
                instructions_in_func = dis.get_instructions(methods[func])
            except Exception as ex:
                # print(ex)
                pass
            else:
                if '__' in func:
                    continue
                for i in instructions_in_func:
                    # print(i)
                    # обнаружил, что если сокет создается из метода класса, то в инструкции он
                    # указывается в opname='LOAD_METHOD', а socket в
                    # 'LOAD_GLOBAL
                    if 'LOAD_' in i.opname:
                        if i.argval not in methods_list:
                            methods_list.append(i.argval)
        for argval in methods_list:
            if argval == 'socket' or argval == 'accept' or argval == 'listen':
                raise TypeError("В классе присутствуют запрещенные методы")
        if 'get_message' in methods_list or 'send_message' in methods_list:
            pass
        else:
            raise TypeError("В классах нет функций работающих с сокетами")


class ServerVerifier(type):

    def __init__(cls, usual_class, bases, methods):
        super().__init__(usual_class, bases, methods)

        methods_list = []
        attrs_list = []

        for func in methods:
            # print(func)
            try:
                instructions_in_func = dis.get_instructions(methods[func])
            except Exception as ex:
                # print(ex)
                pass
            else:
                if '__' in func:
                    continue
                for i in instructions_in_func:
                    # print(i)
                    # обнаружил, что если сокет создается из метода класса, то в инструкции он
                    # указывается в opname='LOAD_METHOD', а socket в
                    # 'LOAD_GLOBAL
                    if 'LOAD_GLOBAL' in i.opname:
                        if i.argval not in methods_list:
                            methods_list.append(i.argval)
                    elif 'LOAD_ATTR' in i.opname:
                        if i.argval not in attrs_list:
                            attrs_list.append(i.argval)
        for argval in methods_list:
            if argval == 'connect':
                raise TypeError("В классе присутствуют запрещенные методы")
        if not ('SOCK_STREAM' in attrs_list and 'AF_INET' in attrs_list):
            raise TypeError("Похоже соединениее не то, которое ожидается.")
