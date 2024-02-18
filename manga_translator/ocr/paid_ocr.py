from typing import List

import numpy as np

from .common import CommonOCR
from ..utils import Quadrilateral


class PaidOCR(CommonOCR):
    def _recognize(self, image: np.ndarray, textlines: List[Quadrilateral], args: dict, verbose: bool = False) -> List[Quadrilateral]:
        raise NotImplemented
