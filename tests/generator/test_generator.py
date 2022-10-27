import pytest
from pathlib import Path
from edge_orm.types_generator import DBConfig, DBVendor, generate, NodeConfig

import tests

db_config_map: dict[str, DBConfig] = {
    "db": DBConfig(
        vendor=DBVendor.edgedb,
        dsn="EDGEDB_DSN",
        hydrate=True,
        nodes={
            "User": NodeConfig(appendix_properties=["created_at", "last_updated_at"])
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
