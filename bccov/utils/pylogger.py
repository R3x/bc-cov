import logging
import os

from colorlog import ColoredFormatter

log_level = logging.INFO
module_log_levels = {}
saved_logs = {}


def set_global_log_level(level):
    global log_level
    log_level = level

    for name, log in saved_logs.items():
        log.setLevel(level)


def set_module_log_level(module, level):
    global module_log_levels
    module_log_levels[module] = level


def get_logger(name, level=None):
    global log_level, saved_logs

    if name in saved_logs:
        return saved_logs[name]

    l = logging.getLogger(name)

    if level is None:
        l.setLevel(log_level)
    else:
        l.setLevel(level)

    logs_path = os.path.join("/tmp", "logs")
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)

    stream_h = logging.StreamHandler()
    # file_h = logging.FileHandler('logs/%s.log' % name)

    formatter = ColoredFormatter(
        "%(asctime)-s %(name)s [%(levelname)s] %(log_color)s%(message)s%(reset)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "purple",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red",
        },
    )
    stream_h.setFormatter(formatter)
    l.addHandler(stream_h)

    # file_h.setFormatter(formatter)
    # l.addHandler(file_h)

    saved_logs[name] = l
    return l
