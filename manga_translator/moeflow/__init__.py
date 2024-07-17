import numpy as np
import re
import json
import manga_translator.utils.textblock as utils_textblock
import manga_translator.utils.generic as utils_generic
from asgiref.sync import async_to_sync
import manga_translator.detection as detection
import manga_translator.ocr as ocr
import manga_translator.translators as translators
import manga_translator.textline_merge as textline_merge
from typing import Any, Awaitable
from PIL import Image


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, utils_textblock.TextBlock):
            return {
                "pts": o.lines,
                "text": o.text,
                "textlines": self.default(o.texts),
            }
        if isinstance(o, utils_generic.Quadrilateral):
            return {
                "pts": o.pts,
                "text": o.text,
                "prob": o.prob,
                "textlines": self.default(o.textlines),
            }
        elif isinstance(o, filter) or isinstance(o, tuple):
            return self.default(list(o))
        elif isinstance(o, list):
            return o
        elif isinstance(o, str):
            return o
        elif isinstance(o, np.ndarray):
            return o.tolist()
        elif isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.floating):
            return float(o)
        else:
            return super().default(o)


def to_json(value: object) -> Any:
    """
    :return: a json-serizable deep clone of `value`
    """
    return json.loads(json.dumps(value, cls=JSONEncoder))


def deserialize_quad_list(text_lines: list[dict]) -> list[utils_generic.Quadrilateral]:
    def create(json_value: dict) -> utils_generic.Quadrilateral:
        optional_args = {
            k: json_value[k]
            for k in ["fg_r", "fg_g", "fg_b", "bg_r", "bg_g", "bg_b"]
            if k in json_value
        }
        return utils_generic.Quadrilateral(
            pts=np.array(json_value["pts"]),
            text=json_value["text"],
            prob=json_value["prob"],
            **optional_args,
        )

    return list(map(create, text_lines))


@async_to_sync
async def async_detection(path_or_url: str, **kwargs: str) -> Awaitable[dict]:
    await detection.prepare(kwargs["detector_key"])
    img = load_rgb_image(path_or_url)
    textlines, mask_raw, mask = await detection.dispatch(
        image=img,
        # detector_key=kwargs['detector_key'],
        **kwargs,
    )
    return {
        "textlines": json.loads(json.dumps(textlines, cls=JSONEncoder)),
        # 'mask_raw': mask_raw,
        # 'mask': mask,
    }


@async_to_sync
async def async_ocr(
    path_or_url: str, **kwargs
) -> Awaitable[list[utils_generic.Quadrilateral]]:
    await ocr.prepare(kwargs["ocr_key"])
    img = load_rgb_image(path_or_url)
    quads = deserialize_quad_list(kwargs["regions"])
    result: list[utils_generic.Quadrilateral] = await ocr.dispatch(
        ocr_key=kwargs["ocr_key"],
        image=img,
        regions=quads,
        args=kwargs,
        verbose=kwargs.get("verbose", False),
    )
    return result


@async_to_sync
async def async_textline_merge(
    *, textlines: list[utils_generic.Quadrilateral], width: int, height: int
) -> list[utils_textblock.TextBlock]:
    return await textline_merge.dispatch(textlines, width, height)


@async_to_sync
async def async_translate(**kwargs) -> Awaitable[list[str]]:
    query = kwargs["query"]
    target_lang = kwargs["target_lang"]
    translator = translators.get_translator(kwargs["translator"])
    if isinstance(translator, translators.OfflineTranslator):
        await translator.download()
        await translator.load("auto", target_lang, device="cpu")
    result = await translator.translate(
        from_lang="auto",
        to_lang=target_lang,
        queries=[query],
    )
    return result


def load_rgb_image(path_or_url: str) -> np.ndarray:
    if re.match(r"^https?://", path_or_url):
        raise NotImplementedError("URL not supported yet")
    img = Image.open(path_or_url)
    img_rgb, img_alpha = utils_generic.load_image(img)
    return img_rgb
