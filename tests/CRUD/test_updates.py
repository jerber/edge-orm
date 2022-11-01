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
    patch = db.UserPatch(
        age=age, friends=db.UserResolver().limit(2).set_update_operation(add=True)
    )
    updated_user = await db.UserResolver().update_one(
        patch=patch, phone_number="+16666666666"
    )
    debug(updated_user)
    assert updated_user.age == age
    with pytest.raises(ResolverException) as e:
        updated_user = await db.UserResolver().update_one(
            patch=patch, phone_number="+16666663093"
        )


@pytest.mark.asyncio
async def test_update_many() -> None:
    age = random.randint(1, 110)
    patch = db.UserPatch(age=age)
    with pytest.raises(ResolverException) as e:
        updated_users = await db.UserResolver().update_many(patch=patch)
    # updates all ages
    # updated_users = await db.UserResolver().update_many(patch=patch, update_all=True)
    updated_users = (
        await db.UserResolver().filter_by(name="Juana").update_many(patch=patch)
    )
    debug(updated_users)
