import logging


logger = logging.getLogger("BeverageOrganiser")

logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "[BeverageOrganiser] %(levelname)s: %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)


def log(message):
    logger.info(message)


def log_error(message):
    logger.error(message)