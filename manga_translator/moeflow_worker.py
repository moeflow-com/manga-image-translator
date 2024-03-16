# consume tasks from moeflow job worker with manga-image-translator code
import re

from celery import Celery
from asgiref.sync import async_to_sync
import manga_translator.detection as detection
import manga_translator.ocr as ocr
import manga_translator.translators as translator
import manga_translator.utils.generic as utils_generic
import manga_translator.utils as utils

import logging
import json

from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, utils_generic.Quadrilateral):
            return {
                'pts': o.pts,
                'text': o.text,
                'prob': o.prob,
                'textlines': list(map(self.default, o.textlines)),
            }
        elif isinstance(o, np.ndarray):
            return o.tolist()
        elif isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.floating):
            return float(o)
        super().default(o)


@celery_app.task(name="tasks.mit.detect_text")
def mit_detect_text(path_or_url: str, **kwargs):
    logger.debug("Running text segmentation %s %s", path_or_url, kwargs)
    result = async_detection(path_or_url, **kwargs)
    logger.debug("Running text segmentation result = %o", result)
    return result


# OCR + detect_textblocks
@celery_app.task(name='tasks.mit.ocr')
def mit_ocr(path_or_url: str, **kwargs):
    logger.debug("Running OCR %s %s", path_or_url, kwargs)
    result = async_ocr(path_or_url, **kwargs)
    logger.debug("Running OCR result = %o", result)
    return result


@celery_app.task(name='tasks.mit_translate')
def mit_translate(path_or_url: str, **kwargs):
    pass


@celery_app.task(name='tasks.mit.inpaint')
def mit_translate(path_or_url: str, **kwargs):
    pass


def load_rgb_image(path_or_url: str) -> np.ndarray:
    if re.match(r'^https?://', path_or_url):
        raise NotImplemented("URL not supported yet")
    img = Image.open(path_or_url)
    img_rgb, img_alpha = utils_generic.load_image(img)
    return img_rgb


@async_to_sync
async def async_detection(path_or_url: str, **kwargs: str):
    await detection.prepare(kwargs['detector_key'])
    img = load_rgb_image(path_or_url)
    text_lines, mask_raw, mask = await detection.dispatch(
        image=img,
        # detector_key=kwargs['detector_key'],
        **kwargs,
    )
    return {
        'text_lines': json.loads(json.dumps(text_lines, cls=JSONEncoder)),
        # 'mask_raw': mask_raw,
        # 'mask': mask,
    }


@async_to_sync
async def async_ocr(path_or_url: str, **kwargs):
    await ocr.prepare(kwargs['ocr_key'])
    img = load_rgb_image(path_or_url)

    result = await ocr.dispatch(
        image=img,
        **kwargs
    )
    return result


@async_to_sync
async def async_translate(image_path: str, dest: str, args_dict: dict):
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
