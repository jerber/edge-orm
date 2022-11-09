from typing import Any, Optional, Type

try:
    from strawberry.unset import UNSET, UnsetType
except ImportError:

    class UnsetType:  # type: ignore
        """Taken from Strawberry: https://strawberry.rocks/"""

        __instance: Optional["UnsetType"] = None

        def __new__(cls: Type["UnsetType"]) -> "UnsetType":
            if cls.__instance is None:
                ret = super().__new__(cls)
                cls.__instance = ret
                return ret
            else:
                return cls.__instance

        def __str__(self) -> str:
            return ""

        def __repr__(self) -> str:
            return "UNSET"

        def __bool__(self) -> bool:
            return False

    UNSET: Any = UnsetType()  # type: ignore

__all__ = ["UNSET", "UnsetType"]
