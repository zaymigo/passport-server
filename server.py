from flask import Flask
from bitarray import bitarray
from time import time
import sys


def read_database_last_update():
    file = open('last_update.txt', 'r')
    date = file.read()
    file.close()
    return date

server_port = 0
for argument in sys.argv:
    print(argument)
    if argument[:7] == '--port=':
        server_port = int(argument[7:])

if server_port == 0:
    print('Required agument --port= not exists!')
    print('Usage: python3 server.py --port=<int>')
    exit()

startTime = time()
databaseLastUpdate = read_database_last_update()

# Создаем битовый массив в памяти
database = bitarray(9999999999)
print('Start initialize database')
csv = open('data/list_of_expired_passports.csv', 'r')

index = 0
for line in csv:
    try:
        num = int(line.replace(",", ""))
        database[num] = True
    except ValueError:
        pass

    index += 1

print('Initialize database complete, db length: ' + str(index) + '(' + str(time() - startTime) + ' sec.)')

print('Запускаем web-server')
app = Flask(__name__)


# Проверка паспорта
@app.route('/check/<passport>', methods=['GET'])
def check_passport(passport):
    if len(passport) != 10:
        return "length error"

    try:
        code = int(passport)
        return str(database[code])
    except ValueError:
        return "format error"


# Дата последнего обновления БД
@app.route('/last-update', methods=['GET'])
def last_update():
    return databaseLastUpdate

if __name__ == '__main__':
    app.run(port=server_port)
