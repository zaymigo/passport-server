# coding=utf-8
import os
import bz2
import datetime
import sys
import xmlrpc.client
import http.client
import time
import logging
import traceback

MAX_APP_SERVER_TIMEOUT = 180
STATE_RUNNING = 20
APP_PATH = '/opt/passport'

logger = logging.getLogger('updater')
logger.setLevel(logging.DEBUG)
loggerHandler = logging.FileHandler(APP_PATH + '/update.log')
loggerFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
loggerHandler.setFormatter(loggerFormatter)
logger.addHandler(loggerHandler)

logger.info('Запускаем процесс обновления БД неактуальных паспортов')

local_file = APP_PATH + '/data/list_of_expired_passports.csv.bz2'
remote_file = '/upload/expired-passports/list_of_expired_passports.csv.bz2'

try:
    # Получаем размер уже имеющегося файла
    current_size = 0
    if os.path.isfile(local_file):
        current_size = os.path.getsize(local_file)
    logger.debug('Размер локального файла: ' + str(current_size))

    # Получаем размер удаленного файла
    connection = http.client.HTTPSConnection('xn--b1ab2a0a.xn--b1aew.xn--p1ai')
    connection.connect()
    connection.request('HEAD', remote_file)

    response = connection.getresponse()
    connection.close()
    remote_size = int(response.getheader('Content-Length', 0))
    logger.debug('Размер файла на сервере: ' + str(remote_size))

    if remote_size == 0:
        logger.critical('Unable fetch remote file size')
        raise Exception('Unable fetch remote file size')

    if int(current_size) != int(remote_size):
        # Удаляем текущую версию файла
        if os.path.isfile(local_file):
            os.remove(local_file)
        logger.debug('Удалем локальный файл: ' + local_file)

        # Загружаем новый файл
        logger.debug('Начинаем чтение файла с сервера: ' + remote_file)
        connection.connect()
        connection.request('GET', remote_file)
        response = connection.getresponse()
        logger.debug('Файл с сервера прочитан, начинаем его сохранение на диск')

        buffer = response.read(2048)
        file = open(local_file, 'wb')
        while buffer:
            file.write(buffer)
            buffer = response.read(2048)
        file.close()
        connection.close()
        logger.debug('Файл сохранен на диск: ' + local_file)
    else:
        logger.debug('Локальная база актуальна, завершаем процесс обновления')

    # Удаляем текущий csv
    logger.debug('Удаляем текущий csv: ' + APP_PATH + '/data/list_of_expired_passports.csv')
    if os.path.isfile(APP_PATH + '/data/list_of_expired_passports.csv'):
        os.remove(APP_PATH + '/data/list_of_expired_passports.csv')

    # Разархивируем скачанный архив
    logger.debug('Начинаем процесс разархивации')
    file = open(APP_PATH + '/data/list_of_expired_passports.csv', 'wb')
    file.write(bz2.decompress(open(local_file, 'rb').read()))
    file.close()
    logger.debug('Файл успешно разархивирован, обновляем информацию о последней дате обновления')

    # Сохраняем информацию о последней дате обновления
    file = open(APP_PATH + '/last_update.txt', 'w')
    file.write(str(datetime.datetime.now()))
    file.close()

    # Перезапускаем сервера через supervisord
    logger.debug('Перезапускаем сервера через supervisord')
    rpc_client = xmlrpc.client.ServerProxy('http://user:123@localhost:9001/RPC2')

    for app_data in sys.argv:
        if app_data == __file__:
            continue

        name, host, port = str(app_data).split(':', 3)
        logger.debug('Перезапускаем сервер ' + name + '(' + host + ':' + port + ')')

        info = rpc_client.supervisor.getProcessInfo(name)
        if info['state'] == STATE_RUNNING:
            rpc_client.supervisor.stopProcess(name)

        rpc_client.supervisor.startProcess(name)
        logger.debug('Сервер ' + name + '(' + host + ':' + port + ') перезапущен, ждем пока он завершит инициализацию')

        connection = http.client.HTTPConnection(host, port)
        connected = False
        connect_start = time.time()
        while not connected:
            try:
                # Ждем пока не соединимся
                connection.connect()
                connected = True
                logger.debug('Сервер ' + name + '(' + host + ':' + port + ') инициализирован')
            except ConnectionRefusedError:
                # Но черезчур долго не ждем
                if time.time() - connect_start > MAX_APP_SERVER_TIMEOUT:
                    connected = True
                    logger.debug('Сервер ' + name + '(' + host + ':' + port + ') не инициализирован, timeout')
                time.sleep(10)

    logger.debug('Все сервера перезапущены и переинициализированы, процесс обновления успешен')
except:
    logger.exception("Unexpected error:" + traceback.format_exc())
    raise

