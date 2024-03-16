# consume tasks from moeflow job worker with manga-image-translator code
import re
from typing import Any, Awaitable

from celery import Celery
from asgiref.sync import async_to_sync
import manga_translator.detection as detection
import manga_translator.ocr as ocr
import manga_translator.translators as translators
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
    # for unknown reason async_ocr returns [[Quad]] instead of [result]
    result, = async_ocr(path_or_url, **kwargs)
    logger.debug("Running OCR result = %s", result)
    return result


@celery_app.task(name='tasks.mit.translate')
def mit_translate(**kwargs):
    logger.debug("Running translate %s %s", kwargs)
    result = async_translate(**kwargs)
    logger.debug("Running translate result = %s", result)
    return result


@celery_app.task(name='tasks.mit.inpaint')
def mit_inpaint(path_or_url: str, **kwargs):
    pass


def load_rgb_image(path_or_url: str) -> np.ndarray:
    if re.match(r'^https?://', path_or_url):
        raise NotImplemented("URL not supported yet")
    img = Image.open(path_or_url)
    img_rgb, img_alpha = utils_generic.load_image(img)
    return img_rgb


def deserialize_quad_list(text_lines: list[dict]) -> list[utils_generic.Quadrilateral]:
    def create(json_value: dict) -> utils_generic.Quadrilateral:
        optional_args = {
            k: json_value[k]
            for k in ['fg_r', 'fg_g', 'fg_b', 'bg_r', 'bg_g', 'bg_b']
            if k in json_value
        }
        return utils_generic.Quadrilateral(
            pts=np.array(json_value['pts']),
            text=json_value['text'],
            prob=json_value['prob'],
            **optional_args
        )

    return list(map(create, text_lines))


@async_to_sync
async def async_detection(path_or_url: str, **kwargs: str):
    await detection.prepare(kwargs['detector_key'])
    img = load_rgb_image(path_or_url)
    textlines, mask_raw, mask = await detection.dispatch(
        image=img,
        # detector_key=kwargs['detector_key'],
        **kwargs,
    )
    return {
        'textlines': json.loads(json.dumps(textlines, cls=JSONEncoder)),
        # 'mask_raw': mask_raw,
        # 'mask': mask,
    }


@async_to_sync
async def async_ocr(path_or_url: str, **kwargs):
    await ocr.prepare(kwargs['ocr_key'])
    img = load_rgb_image(path_or_url)
    regions = deserialize_quad_list(kwargs['regions'])
    result = await ocr.dispatch(
        ocr_key=kwargs['ocr_key'],
        image=img,
        regions=regions,
        args=kwargs,
        verbose=kwargs.get('verbose', False),
    )
    return json.loads(json.dumps(result, cls=JSONEncoder)),


@async_to_sync
async def async_translate(**kwargs) -> Awaitable[list[str]]:
    query = kwargs['query']
    target_lang = kwargs['target_lang']
    translator = translators.get_translator(kwargs['translator'])
    if isinstance(translator, translators.OfflineTranslator):
        await translator.download()
        await translator.load('auto', target_lang, device='cpu')
    result = await translator.translate(
        from_lang='auto',
        to_lang=target_lang,
        queries=[query],
    )
    return result
