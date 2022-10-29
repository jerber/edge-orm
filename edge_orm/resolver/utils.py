from edge_orm.node.models import Node, Insert, Patch


def model_to_set_bracket(*, model: Insert | Patch) -> str:
    """takes in a model dictionary and returns a string that represents a mutation with this dictionary
    eg: {"name": "Jeremy Berman", "age": UNSET, "last_updated": 2022...} -> { name := <str>$name, age := <int>{}, ...}"""
    ...
