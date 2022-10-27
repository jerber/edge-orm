import uuid
from datetime import datetime
from edge_orm import Node
from devtools import debug


class User(Node):
    name: str
    age: int
    created_at: datetime

    class Edge:
        appendix_properties = {"created_at"}
        computed_properties = {"names_of_friends"}


def test_immutability() -> None:
    u = User(name="Charlotte", age=12, created_at=datetime.now(), id=uuid.uuid4())
    debug(u)
