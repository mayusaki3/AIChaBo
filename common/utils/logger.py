# -*- coding: utf-8 -*-
import logging
from .redact import redact

_logger = logging.getLogger("aichabo")
if not _logger.handlers:
    h = logging.StreamHandler()
    fmt = logging.Formatter("[%(levelname)s] %(message)s")
    h.setFormatter(fmt)
    _logger.addHandler(h)
    _logger.setLevel(logging.INFO)

def log_info(msg: str):  _logger.info(msg)
def log_warn(msg: str):  _logger.warning(msg)
def log_error(msg: str): _logger.error(redact(msg))
