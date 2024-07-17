# consume tasks from moeflow job worker with manga-image-translator code
import re
from typing import Any, Awaitable

from celery import Celery
import manga_translator.utils.generic as utils_generic
import manga_translator.utils.textblock as utils_textblock
# FIXME: impl better translator , maybe with Langchain
# FIXME: maybe create a different translators package

import logging
import json
import os
import dotenv

import numpy as np
from manga_translator.moeflow import to_json, async_textline_merge, async_detection, async_ocr, async_translate, load_rgb_image

dotenv.load_dotenv()
BROKER_URL = os.environ.get('CELERY_BROKER_URL')
BACKEND_URL = os.environ.get('CELERY_BACKEND_URL')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

celery_app = Celery(
    "manga-image-translator-moeflow-worker",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    result_expires = 7 * 24 * 60 * 60, # 7d
)


@celery_app.task(name="tasks.mit.detect_text")
def mit_detect_text(path_or_url: str, **kwargs):
    logger.debug("Running text segmentation %s %s", path_or_url, kwargs)
    result = async_detection(path_or_url, **kwargs)
    logger.debug("Running text segmentation result = %s", result)
    return result


# OCR + detect_textblocks + merge_textlines
@celery_app.task(name='tasks.mit.ocr')
def mit_ocr(path_or_url: str, **kwargs):
    logger.debug("Running OCR %s %s", path_or_url, kwargs)
    # for unknown reason async_ocr returns [[Quad]] instead of [result]
    textlines = async_ocr(path_or_url, **kwargs)
    # return json.loads(json.dumps(result, cls=JSONEncoder)),
    logger.debug("Running OCR result = %s", textlines)

    img_w, img_h, *_rest = load_rgb_image(path_or_url).shape

    min_text_length = kwargs.get('min_text_length', 0)
    text_blocks_all: list[utils_textblock.TextBlock] = async_textline_merge(
        textlines=textlines,
        width=img_w,
        height=img_h)

    # logger.debug("text_blocks_all = %s", text_regions_all)
    text_blocks = filter(
        lambda r: len(r.text) > min_text_length and utils_generic.is_valuable_text(r.text),
        text_blocks_all)

    return to_json(text_blocks)


@celery_app.task(name='tasks.mit.translate')
def mit_translate(**kwargs):
    logger.debug("Running translate %s", kwargs)
    result = async_translate(**kwargs)
    logger.debug("Running translate result = %s", result)
    return result


@celery_app.task(name='tasks.mit.inpaint')
def mit_inpaint(path_or_url: str, **kwargs):
    raise NotImplementedError()

