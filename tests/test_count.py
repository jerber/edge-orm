import pytest
from tests.generator.gen import db_hydrated as db
from devtools import debug


@pytest.mark.asyncio
async def test_count() -> None:
    users = (
        await db.UserResolver()
        .include(names_of_friends=True)
        .filter("exists .friends")
        .friends()
        .friends_Count()
        .friends_Count(db.UserResolver().limit(1))
        .limit(10)
        .query()
    )
    for user in users:
        friends_count = await user.friends_Count()
        friends_count_limit = await user.friends_Count(db.UserResolver().limit(1))
        print(
            f"{user.name}, {user.names_of_friends=}, {friends_count=}, {friends_count_limit=}"
        )
        assert not friends_count_limit > 1
        assert friends_count >= friends_count_limit
