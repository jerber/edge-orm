from uuid import UUID
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random
import pytest
from edge_orm import (
    ResolverException,
    resolver_enums,
    logger,
    helpers,
    ExecuteConstraintViolationException,
)
from tests.generator.gen import db_hydrated as db
from devtools import debug
import tests
from faker import Faker
from devtools import debug
import time

fake = Faker()


def build_insert(name: str = None, phone_number: str = None) -> db.UserInsert:
    name = name or fake.name()
    phone_number = phone_number or fake.phone_number()
    return db.UserInsert(phone_number=phone_number, name=name)


@pytest.mark.asyncio
async def test_insert_one() -> None:
    insert = build_insert()
    new_user = await db.UserResolver().insert_one(insert=insert)

    yes_user = await db.UserResolver().gerror(id=new_user.id)
    debug(yes_user)


@pytest.mark.asyncio
async def test_insert_many() -> None:
    n = 5
    inserts = [build_insert() for _ in range(n)]
    for insert in inserts:
        insert.age = None
    inserts[-1].age = 30
    new_users = await db.UserResolver().insert_many(inserts=inserts)
    new_user_ids = {u.id for u in new_users}
    assert len(new_users) == n

    yes_users = await db.UserResolver().filter_in(id=list(new_user_ids)).query()
    assert {u.id for u in yes_users} == new_user_ids

    inserts = [build_insert() for _ in range(n)]
    inserts[-1].age = 30
    with pytest.raises(ResolverException):
        new_users = await db.UserResolver().insert_many(inserts=inserts)


@pytest.mark.asyncio
async def test_insert_many_with_links() -> None:
    # now links
    insert = build_insert()
    insert.email = fake.email()
    insert.friends = db.UserResolver().filter_by(phone_number="+16666666666")
    insert2 = build_insert()
    insert2.email = fake.email()
    insert2.friends = db.UserResolver().filter_by(phone_number="+15559710349")
    new_users = (
        await db.UserResolver()
        .include_appendix_properties()
        .include_computed_properties()
        # .friends(db.UserResolver().filter_by(phone_number="+16666666666"))
        # .friends()
        .insert_many(inserts=[insert, insert2])
    )
    debug(new_users)


@pytest.mark.asyncio
async def test_insert_with_conflict() -> None:
    # now links
    phone_number = "945-632-7731"
    insert = build_insert(phone_number=phone_number)
    rez = (
        db.UserResolver()
        .include_appendix_properties()
        .include_computed_properties()
        .friends()
        .extra_field("friend_ids", ".friends.id", conversion_func=UUID)
    )
    with pytest.raises(ExecuteConstraintViolationException):
        new_user = await rez.insert_one(insert)
    new_user = await rez.insert_one(
        insert=insert, upsert_given_conflict_on="phone_number"
    )
    debug(new_user)
    assert new_user.name == insert.name

    new_insert = build_insert(phone_number=phone_number)
    user_returned = await rez.insert_one(
        insert=new_insert, return_model_for_conflict_on="phone_number"
    )
    assert user_returned.name == insert.name

    assert user_returned.last_updated_at > datetime.now(
        tz=ZoneInfo("America/New_York")
    ) - timedelta(seconds=4)
    custom_returned = await rez.insert_one(
        insert=insert,
        custom_conflict_on_str="UNLESS CONFLICT ON .phone_number else ( UPDATE User SET { last_updated_at := datetime_current() - <cal::relative_duration>'1 year' } )",
    )
    assert custom_returned.last_updated_at < datetime.now(
        tz=ZoneInfo("America/New_York")
    ) - timedelta(minutes=10)

    print("CCC", user_returned._cache)


@pytest.mark.asyncio
async def test_caching():
    rez = (
        db.UserResolver()
        .include_appendix_properties()
        .include_computed_properties()
        .friends(db.UserResolver().include(names_of_friends=True, ids_of_friends=True))
        .extra_field("friend_ids", ".friends.id", conversion_func=UUID)
    )

    user = await rez.copy().gerror(phone_number="+16666666666")

    debug(user.computed)
    assert len(user.computed["friend_ids"]) > 1
    debug(user)
    debug(user._cache)
    start = time.time()
    friends = await user.friends(db.UserResolver().include(names_of_friends=True))
    assert time.time() - start < 0.01
    debug(friends)

    users = await rez.query()
    debug(users)
