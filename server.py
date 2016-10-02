from flask import Flask
from bitarray import bitarray
from time import time


startTime = time()
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

print('Запускаем web-server для работки запросов')
app = Flask(__name__)


@app.route('/<passport>', methods=['GET'])
def check_passport(passport):
    if len(passport) != 10:
        return "incorrect passport number size"

    try:
        code = int(passport)
        return str(database[code])
    except ValueError:
        return "Incorrect passport value"

if __name__ == '__main__':
    app.run()
