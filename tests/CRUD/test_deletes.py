from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import pytest
from edge_orm import ResolverException, resolver_enums, logger, helpers
from tests.generator.gen import db_hydrated as db
from devtools import debug
import tests
from faker import Faker
from devtools import debug

fake = Faker()


def build_insert(name: str = None) -> db.UserInsert:
    name = name or fake.name()
    return db.UserInsert(phone_number=fake.phone_number(), name=name)


@pytest.mark.asyncio
async def test_delete_one() -> None:
    insert = build_insert()
    new_user = await db.UserResolver().insert_one(insert=insert)

    yes_user = await db.UserResolver().gerror(id=new_user.id)
    debug(yes_user)

    deleted_user = await db.UserResolver().delete_one(id=new_user.id)
    debug(deleted_user)
    with pytest.raises(ResolverException):
        no_user = await db.UserResolver().gerror(id=deleted_user.id)
        debug(no_user)


@pytest.mark.asyncio
async def test_delete_many() -> None:
    consistent_name = fake.name()
    n = 5
    inserts = [build_insert(name=consistent_name) for _ in range(n)]

    new_users = [
        await db.UserResolver().insert_one(insert=insert) for insert in inserts
    ]
    new_user_ids = {u.id for u in new_users}
    assert {consistent_name} == {u.name for u in new_users}
    assert len(new_users) == n

    with pytest.raises(ResolverException):
        deleted_users = await db.UserResolver().delete_many()

    deleted_users = (
        await db.UserResolver().filter_by(name=consistent_name).delete_many()
    )
    assert len(deleted_users) == n
    assert {u.id for u in deleted_users} == new_user_ids

    for id in new_user_ids:
        with pytest.raises(ResolverException):
            no_user = await db.UserResolver().gerror(id=id)
