module default {

    abstract type DateModel {
        required property created_at -> datetime {
            default := datetime_current();
        }
        required property last_updated_at -> datetime {
            default := datetime_current();
        }
    }

    scalar type UserRole extending enum<buyer, seller, admin>;

    type User extending DateModel {
        required property name -> str;
        required property phone_number -> str {
            readonly := true;
            constraint exclusive;
        }
        property age -> int16;
        multi link friends -> User {
            on target delete allow;
        }

        property names_of_friends := .friends.name;
        property ids_of_friends := .friends.id;

        property user_role -> UserRole;

        property images -> array<json>;
        property email -> str;
    }

}
