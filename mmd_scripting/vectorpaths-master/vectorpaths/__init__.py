"""Path package; mainly for fitting cubic beziers to points.
"""

# import numpy as np
# import matplotlib.pyplot as plt
import logging

__author__ = 'Chris Arridge'
__version__ = '0.2'

_path_logger = logging.getLogger(__name__)

from .bezier import CubicBezier
from .fitcurves import fit_cubic_bezier
