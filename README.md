# Passport Server

Приложение для проверки паспорта по списку недействительных паспортов, по базе данных [Главного управления по вопросам миграции МВД России](http://services.fms.gov.ru/info-service.htm?sid=2000)

## Описание

Приложение состоит из трех компонентов:

1. nginx: проксирует запросы к нескольким экземплярам web-server (go lang)
2. web-server для обработки запросов на проверку паспорта (python)
3. updater для проверки и обновления БД (python)

## Установка

Загрузите содержимое репозитория в директорию /opt/passport
Установите следующие пакеты 
`sudo apt-get install gcc python3 python3-dev python3-pip python python-setuptools nginx`

### Установка зависимостей для python3

**bitarray**

```shell
wget https://pypi.python.org/packages/0a/da/9f61d28a20c42b4963334efacfd257c85150ede96d0cd2509b37da69da47/bitarray-0.8.1.tar.gz
tar xzf bitarray-0.8.1.tar.gz
cd bitarray-0.8.1
sudo python3 setup.py install
```

**Flask**

```shell
sudo pip install flask
```

### Конфигурация

Возможны различные конфигурации, с учетом выполнения приложения на нескольких серверах. В данном случае рассматривается установка приложения на одном сервере.

**Установите supervisord, добавте в него следующие приложения:**

```lang=ini
[program:passport_proxy]
directory=/opt/passport
command=./bin/proxy --port=5000 --app=5001,5002


[program:passport_web1]
directory=/opt/passport
command=python3 server.py --port=5001


[program:passport_web2]
directory=/opt/passport
command=python3 server.py --port=5002
```

_Два экземпляра server.py нужны для того чтобы пока один сервер недоступен и обновляется, запросы обрабатывал другой сервер_

**Добавьте в crontab команду на проверку обновлений, рекомендуемая периодичность: 1 раз в час**

```crontab
0 * * * *   python3 /opt/passport/updater.py passport_web1:127.0.0.1:5001 passport_web2:127.0.0.1:5002
```

**Настройте nginx для проксирования на оба приложения, пример конфига:**

```nginx
upstream passport_apps {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
}

server {
    server_name passport-server.local;
    listen 80;

    location / {
        proxy_pass http://passport_apps;
    }
}
```

После этого приложение полностью настроено, и готово к работе.

## Инициализация

 1. Выполните команду `python3 update.py` без аргументов, для начальной загрузки БД (обычно занимает минут 5, скрипт скачивает архив ~350 мегобайт, и разархивирует его).
 2. Перезагрузите апп сервера через supervisord
 3. Подождите минутку пока 1.3 гига загружаются в память...

## Использование

Для проверки паспортов необходимо отправлять `GET` запрос на хост сконфигурированный в nginx.

Пример для проверки паспорта 1234 567890:
`curl passport-server.local/check/1234567890`

Возможные ответы:

  * **length error** Некорректная длина паспорта (должна быть 10 символов)
  * **format error** Некорректные символы (допустимы только цифры)
  * **True** Паспорт пристутвует с списке недействительных паспортов
  * **False** Паспорт отсутствует в списке недействительных паспортов

Для получения даты последнего обновления БД выполните запрос:
`curl passport-server.local/last-update`

И получите дату в формате `2016-10-02 19:23:24.376351`
