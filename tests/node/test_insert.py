import uuid
from datetime import datetime
from edge_orm import Node, Insert, UNSET, UnsetType
from devtools import debug
from tests.node.test_node import User
from devtools import debug


class UserInsert(Insert):
    id: uuid.UUID | UnsetType = UNSET
    name: str
    age: int
    optional_description: str | None | UnsetType = UNSET


def test_insert() -> None:
    insert = UserInsert(name="hi", age=3, optional_description=None)
    debug(insert)
