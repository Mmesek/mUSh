import logging

logger = logging.getLogger("mUSHelper")

if True:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)
