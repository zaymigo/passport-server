import datetime
import logging
import pika
import json
import traceback

APP_PATH = '/opt/passport'
QUEUE_NAME = 'monitoring_service_queue'
EXCHANGE_NAME = 'event_monitoring_exchange'
EVENT_NAME = 'test'
RABBIT_HOST = '127.0.0.1'
RABBIT_PORT = 5672
RABBIT_USER = 'guest'
RABBIT_PWD = 'guest'
RABBIT_VHOST = '/'


logger = logging.getLogger('monitoring')
logger.setLevel(logging.DEBUG)
loggerHandler = logging.FileHandler(APP_PATH + '/monitoring.log')
loggerFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
loggerHandler.setFormatter(loggerFormatter)
logger.addHandler(loggerHandler)

logger.info('Запускаем процесс проверки даты последнего обновления БД неактуальных паспортов')

connectionQueue = pika.BlockingConnection(
    pika.ConnectionParameters(
        RABBIT_HOST,
        RABBIT_PORT,
        RABBIT_VHOST,
        pika.credentials.PlainCredentials(RABBIT_USER, RABBIT_PWD)
    )
)
local_log_file = APP_PATH + '/last_update.txt'
try:
    file = open(local_log_file, 'r')
    first_line = file.readline()
    date = datetime.datetime.strptime(first_line, '%Y-%m-%d %H:%M:%S.%f')
except:
    logger.exception("Unexpected error:" + traceback.format_exc())
    raise
message = {
    "type": "passport.update.done",
    "date": int(date.timestamp())
}

channel = connectionQueue.channel()
channel.queue_declare(queue=QUEUE_NAME, durable=True)
try:
    channel.basic_publish(exchange=EXCHANGE_NAME,
                      routing_key='',
                      body=json.dumps(message))
except:
    logger.exception("Unexpected error:" + traceback.format_exc())
    raise
connectionQueue.close()
