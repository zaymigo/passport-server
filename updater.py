import os
import bz2
import datetime
import sys
import xmlrpc.client
import http.client
import time

MAX_APP_SERVER_TIMEOUT = 180
STATE_RUNNING = 20

local_file = os.path.curdir + '/data/list_of_expired_passports.csv.bz2'
remote_file = '/upload/expired-passports/list_of_expired_passports.csv.bz2'

# Получаем размер уже имеющегося файла
current_size = 0
if os.path.isfile(local_file):
    current_size = os.path.getsize(local_file)

# Получаем размер удаленного файла
connection = http.client.HTTPSConnection('guvm.mvd.ru')
connection.connect()
connection.request('HEAD', remote_file)

response = connection.getresponse()
connection.close()
remote_size = int(response.getheader('Content-Length', 0))

if remote_size == 0:
    raise Exception('Unable fetch remote file size')

if current_size != remote_size:
    # Удаляем текущую версию файла
    if os.path.isfile(local_file):
        os.remove(local_file)
    # Загружаем новый файл
    connection.connect()
    connection.request('GET', remote_file)
    response = connection.getresponse()

    buffer = response.read(2048)
    file = open(local_file, 'wb')
    while buffer:
        file.write(buffer)
        buffer = response.read(2048)
    file.close()
    connection.close()

    # Удаляем текущий csv
    os.remove(os.path.curdir + '/data/list_of_expired_passports.csv')

    # Разархивируем скачанный архив
    file = open(os.path.curdir + '/data/list_of_expired_passports.csv', 'wb')
    file.write(bz2.decompress(open(local_file, 'rb').read()))
    file.close()

    # Сохраняем информацию о последней дате обновления
    file = open(os.path.curdir + '/last_update.txt', 'w')
    file.write(str(datetime.datetime.now()))
    file.close()

    # Перезапускаем сервера через supervisord
    rpc_client = xmlrpc.client.ServerProxy('http://user:123@localhost:9001/RPC2')

    for app_data in sys.argv:
        if app_data == __file__:
            continue

        name, host, port = str(app_data).split(':', 3)
        info = rpc_client.supervisor.getProcessInfo(name)
        if info['state'] == STATE_RUNNING:
            rpc_client.supervisor.stopProcess(name)

        rpc_client.supervisor.startProcess(name)

        connection = http.client.HTTPConnection(host, port)
        connected = False
        connect_start = time.time()
        while not connected:
            try:
                # Ждем пока не соединимся
                connection.connect()
                connected = True
            except ConnectionRefusedError:
                # Но черезчур долго не ждем
                if time.time() - connect_start > MAX_APP_SERVER_TIMEOUT:
                    connected = True
                time.sleep(10)
