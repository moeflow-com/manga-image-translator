# consume tasks from moeflow job worker with manga-image-translator code
from celery import Celery
from asgiref.sync import async_to_sync
import manga_translator.detection as detection
import manga_translator.ocr as ocr
import manga_translator.translators as translator

from .detection import DETECTORS, dispatch as dispatch_detection, prepare as prepare_detection
from .ocr import OCRS, dispatch as dispatch_ocr, prepare as prepare_ocr
from .textline_merge import dispatch as dispatch_textline_merge

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
def detect_textblocks(image_path: str, args=None):
    detector_args = {
        'detector': 'default',  # see detecton/__init__.py
        # 'img_rgb': from image
        **(args or {})
    }


@async_to_sync
async def do_detect(image_path: str, args: dict):
    await detection.prepare(args['detector'])
    result = await detection.dispatch(image_path, **args)
    return {}


@celery_app.task
def translate(blocks: list[object], args: dict):
    pass


async def do_translate(image_path: str, dest: str, args_dict: dict):
    await translator.prepare(args['translator'])

    ocr_dict = {
        'ocr': '48px',  # reportedly to work best
        # textlines: from detector
        # TODO more
    }

    translate_dict = {

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
