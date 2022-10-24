from enum import Enum


class FilterConnector(str, Enum):
    AND = " AND "
    OR = " OR "
