module default {

    abstract type DateModel {
        required property created_at -> datetime {
            default := datetime_current();
        }
        required property last_updated_at -> datetime {
            default := datetime_current();
        }
    }

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
    }

}
