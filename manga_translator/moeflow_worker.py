# consume tasks from moeflow job worker with manga-image-translator code
from celery import Celery
from manga_translator import MangaTranslator
from asgiref.sync import async_to_sync

env = {
    "RABBITMQ_USER": 'moeflow',
    "RABBITMQ_PASS": 'PLEASE_CHANGE_THIS',
    'RABBITMQ_VHOST_NAME': 'moeflow',
    'MONGODB_USER': 'moeflow',
    'MONGODB_PASS': 'PLEASE_CHANGE_THIS',
    'MONGODB_DB_NAME': 'moeflow',
}


celery_app = Celery(
    "manga-image-translator-moeflow-worker",
    broker=f"amqp://{env['RABBITMQ_USER']}:{env['RABBITMQ_PASS']}@moeflow-rabbitmq:5672/{env['RABBITMQ_VHOST_NAME']}",
    backend=f"mongodb://{env['MONGODB_USER']}:{env['MONGODB_PASS']}@moeflow-mongodb:27017/{env['MONGODB_DB_NAME']}?authSource=admin",
    mongodb_backend_settings={
        "database": env["MONGODB_DB_NAME"],
        "taskmeta_collection": "celery_taskmeta",
    })


@celery_app.task
def add(x, y):
    return x + y


@celery_app.task
def translate(image_path: str, dest: str, args_dict: dict):
    detector_args = {
        'detector': 'default',  # see detecton/__init__.py
        # 'img_rgb': from image
        # 'detect_size': 48,
    }

    ocr_dict = {
        'ocr': '48px',  # reportedly to work best
        # textlines: from detector
        # TODO more
    }

    translate_dict = {

    }

    inpaint_dict = {

    }

    ctx_dict = {
        # **args_dict,
        # upscale_ratio
        **detector_args,
        **ocr_dict,
        **translate_dict,
        **ocr_dict
    }
    return do_translate(image_path, dest, ctx_dict)


@async_to_sync
async def do_translate(image_path: str, dest_image_path: str, args_dict: dict):
    translator = MangaTranslator()

    await translator.translate_file(image_path, dest_image_path, args_dict)
