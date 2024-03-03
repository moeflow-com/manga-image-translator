# consume tasks from moeflow job worker with manga-image-translator code
from celery import Celery

env = {
    "RABBITMQ_USER":  'moeflow',
    "RABBITMQ_PASS":  'PLEASE_CHANGE_THIS',
    'RABBITMQ_VHOST_NAME': 'moeflow',
    'MONGODB_USER': 'moeflow',
    'MONGODB_PASS': 'PLEASE_CHANGE_THIS',
    'MONGODB_DB_NAME': 'moeflow',
}


celery_app = Celery(
    "manga-image-translator-moeflow-worker",
    broker =f"amqp://{env['RABBITMQ_USER']}:{env['RABBITMQ_PASS']}@moeflow-rabbitmq:5672/{env['RABBITMQ_VHOST_NAME']}",
    backend= f"mongodb://{env['MONGODB_USER']}:{env['MONGODB_PASS']}@moeflow-mongodb:27017/{env['MONGODB_DB_NAME']}?authSource=admin",
    mongodb_backend_settings={
        "database": env["MONGODB_DB_NAME"],
        "taskmeta_collection": "celery_taskmeta",
    })


@celery_app.task
def add(x, y):
    return x + y
