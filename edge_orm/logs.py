import typing as T
import logging
from enum import Enum

FORMAT_STR = "%(asctime)s | %(process)d | %(name)s |  %(levelname)s: %(message)s"


class Color(str, Enum):
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    PURPLE = 5
    TEAL = 6
    GREY = 7


RESET_STR = "\x1b[0m"


def format_str_from_color(color: Color, bold: bool = False) -> str:
    bold_str = "20" if not bold else "1"
    color_str = f"\x1b[3{color.value};{bold_str}m"
    format_str = f"{color_str} {FORMAT_STR} {RESET_STR}"
    return format_str


COLORS = dict[int, Color]
FORMATS = dict[int, str]

DEFAULT_FORMATS: FORMATS = {
    logging.DEBUG: format_str_from_color(Color.TEAL),
    logging.INFO: format_str_from_color(Color.PURPLE),
    logging.WARNING: format_str_from_color(Color.YELLOW),
    logging.ERROR: format_str_from_color(Color.RED, bold=False),
    logging.CRITICAL: format_str_from_color(Color.RED, bold=True),
}


def formats_from_colors(color_map: COLORS) -> FORMATS:
    return {k: format_str_from_color(v) for k, v in color_map.items()}


class CustomFormatter(logging.Formatter):
    def __init__(
        self,
        formats: FORMATS | None = None,
        no_colors: bool = False,
        *args: T.Any,
        **kwargs: T.Any,
    ):
        super().__init__(*args, **kwargs)
        self.formats = formats or DEFAULT_FORMATS
        self.no_colors = no_colors

    def format(self, record: logging.LogRecord) -> str:
        if self.no_colors:
            format_str = FORMAT_STR
        else:
            format_str = self.formats[record.levelno]
        formatter = logging.Formatter(format_str)
        return formatter.format(record)


def create_logger(
    name: str,
    level: T.Any = logging.DEBUG,
    colors_map: COLORS = None,
    no_colors: bool = False,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level=level)
    handler = logging.StreamHandler()
    if not colors_map:
        formats = None
    else:
        formats = formats_from_colors(colors_map)
    handler.setFormatter(CustomFormatter(formats=formats, no_colors=no_colors))
    logger.addHandler(handler)
    return logger


logger = create_logger(name="EdgeORM")
