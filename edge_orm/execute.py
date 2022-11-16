import typing as T
import time
import orjson
from enum import Enum
import edgedb
from edge_orm import logger
from edge_orm.span import span


class ExecuteException(Exception):
    pass


class ExecuteConstraintViolationException(ExecuteException):
    pass


MUTATION_ACTIONS = {"insert ", "update ", "delete "}


def operation_from_query_str(query_str: str) -> str:
    s = query_str.lower()
    for action in MUTATION_ACTIONS:
        if action in s:
            return "mutation"
    return "query"


def check_enum(v: T.Any) -> T.Any:
    if isinstance(v, Enum):
        return v.value
    return v


async def query(
    *,
    client: edgedb.AsyncIOClient,
    query_str: str,
    variables: dict[str, T.Any] | None = None,
    only_one: bool,
) -> T.Any | None:
    if variables is None:
        variables = {}
    # TODO usually would simplify vars here but should do this in earlier step
    query_func = client.query_json if not only_one else client.query_single_json
    # turn enums into values
    variables = {k: check_enum(v) for k, v in variables.items()}
    start = time.time()
    try:
        with span(
            op=f"edge-orm.{operation_from_query_str(query_str)}",
            description=query_str[:200],
        ):
            json_str = await query_func(query=query_str, **variables)
        with span(op=f"orjson.loads", description=f"{len(json_str)=}"):
            response_dict = orjson.loads(json_str)
    except edgedb.errors.ConstraintViolationError as e:
        logger.error(f"{e=}")
        if "is prohibited by link target policy" in str(e):
            raise e
        if "violates exclusivity constraint" in str(e):
            field_name = str(e).split(" ")[0].replace("_", " ")
            raise ExecuteConstraintViolationException(
                f"That {field_name} already exists in our system."
            )
        raise e
    except Exception as e:
        logger.error(
            f"EdgeDB Query Exception: {e}, query_str and variables: {query_str=}, {variables=}"
        )
        raise e
    took_ms = round((time.time() - start) * 1_000, 2)
    logger.debug(query_str)
    logger.debug(f"took {took_ms} ms")
    return response_dict
