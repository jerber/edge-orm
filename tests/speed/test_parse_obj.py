import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from edge_orm import ResolverException, resolver_enums, logger, helpers
from tests.generator.gen import db_hydrated as db
import tests
from devtools import debug


def test_build_user() -> None:
    user = db.User(
        id=uuid.uuid4(),
        phone_number=f"+1{helpers.random_digits(10)}",
        name="Huan PR",
        age=11,
        names_of_friends=["Juandala", "huc"],
        # ids_of_friends=["jhi"],
    )
    # user._ids_of_friends = ["juds", "dsj"]
    # debug(user)
    debug(user.__fields_set__)
    debug(user.set_fields_)
    debug(user.__fields__.keys())

    print(f"{user.names_of_friends=}")
    assert user.names_of_friends == set(["Juandala", "huc"])
    # print(f"{user.ids_of_friends=}")
    # print(f"{user._created_at}")
    # print(f"{user._last_updated}")
    debug(user)
