from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import pytest
from edge_orm import ResolverException, resolver_enums, logger
from tests.generator.gen import db_hydrated as db
from devtools import debug
import tests
from devtools import debug


@pytest.mark.asyncio
async def test_update_one() -> None:
    age = random.randint(1, 110)
    patch = db.UserPatch(age=age)
    updated_user = await db.UserResolver().update_one(
        patch=patch, phone_number="+16666666666"
    )
    debug(updated_user)
    assert updated_user.age == age
