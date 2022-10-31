from uuid import UUID
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from edge_orm import ResolverException, resolver_enums, logger
from tests.generator.gen import db_hydrated as db
from devtools import debug
import tests
from devtools import debug


@pytest.mark.asyncio
async def test_update_many() -> None:
    patch = db.UserPatch(age=12)
    updated_user = await db.UserResolver().update_one(
        patch=patch, phone_number="+16666666666"
    )
    debug(updated_user)
