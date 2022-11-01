from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from edge_orm import ResolverException, resolver_enums, logger
from tests.generator.gen import db_hydrated as db
from devtools import debug
import tests
from faker import Faker

fake = Faker()
import asyncio


@pytest.mark.asyncio
async def test_merge() -> None:
    rez = (
        db.UserResolver()
        .include_appendix_properties()
        .include_computed_properties()
        .friends(
            db.UserResolver()
            .include(names_of_friends=True, ids_of_friends=True)
            .limit(1)
        )
        .friends(
            db.UserResolver()
            .include_appendix_properties()
            .include(ids_of_friends=True)
            .limit(2)
            .friends()
        )
    )
    user = await rez.gerror(phone_number="+16666666666")
    # debug(user)
    # debug(user._cache)
    friends = await user.friends(
        db.UserResolver().include(ids_of_friends=True).limit(2)
    )
    debug(friends)
