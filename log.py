import logging

logger = logging.getLogger("New Words Loss")
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(filename)s->%(funcName)s():]\n%(levelname)8s: %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
