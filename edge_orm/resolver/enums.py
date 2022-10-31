from enum import Enum


class FilterConnector(str, Enum):
    AND = " AND "
    OR = " OR "


class UpdateOperation(str, Enum):
    REPLACE = ":="
    ADD = "+="
    REMOVE = "-="
