import random
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


def build_insert(name: str = None, phone_number: str = None) -> db.UserInsert:
    name = name or fake.name()
    phone_number = phone_number or fake.phone_number()
    return db.UserInsert(
        phone_number=phone_number,
        name=name,
        email=fake.email(),
        age=random.randint(1, 100),
        user_role=db.enums.UserRole.buyer,
        friends=db.UserResolver().limit(10),
    )


@pytest.mark.asyncio
async def test_add_users(n: int = 200) -> None:
    inserts = [build_insert() for _ in range(n)]
    # debug(inserts)
    users = (
        await db.UserResolver()
        .friends()
        .include(names_of_friends=True)
        .insert_many(inserts=inserts)
    )
    debug(users)


@pytest.mark.asyncio
async def test_large_query() -> None:
    users = (
        await db.UserResolver()
        .include_appendix_properties()
        .friends(db.UserResolver().include_appendix_properties())
        .limit(100)
        .query()
    )
    # for user in users:
    #     print(len(await user.friends()))
