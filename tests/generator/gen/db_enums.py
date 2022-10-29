from enum import Enum


class UserRole(str, Enum):
    buyer = "buyer"
    seller = "seller"
    admin = "admin"
