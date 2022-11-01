import pytest
from pathlib import Path
from edge_orm.types_generator import (
    DBConfig,
    DBVendor,
    generate,
    NodeConfig,
    PropertyConfig,
)

import tests

db_config_map: dict[str, DBConfig] = {
    "db": DBConfig(
        vendor=DBVendor.edgedb,
        dsn="EDGEDB_DSN",
        hydrate=True,
        nodes={
            "User": NodeConfig(
                appendix_properties=[
                    "created_at",
                    "last_updated_at",
                    "user_role",
                    "images",
                    "email",
                ],
                basemodel_properties={
                    "email": PropertyConfig(
                        module_name="EmailStr",
                        module_path="pydantic",
                        validate_as_basemodel=False,
                    )
                },
                mutate_on_update={"last_updated_at": "datetime_current()"},
            )
        },
    )
}


@pytest.mark.asyncio
async def test_generate() -> None:
    await generate(
        db_config_map=db_config_map,
        output_path=Path(__file__).parent / "gen",
        include_strawberry=False,
    )
