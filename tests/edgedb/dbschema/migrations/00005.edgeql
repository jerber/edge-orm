CREATE MIGRATION m125hw4qgsar6fzcby2l6ntghpge5c7ambllcclju3z7pjbyg3g6pa
    ONTO m1lddio2htrzjhtc3k7mynk7qdjcezmip5y4uv3aawas32grxkl2sq
{
  CREATE ABSTRACT TYPE default::DateModel {
      CREATE REQUIRED PROPERTY created_at -> std::datetime {
          SET default := (std::datetime_current());
      };
      CREATE REQUIRED PROPERTY last_updated_at -> std::datetime {
          SET default := (std::datetime_current());
      };
  };
  ALTER TYPE default::User EXTENDING default::DateModel LAST;
};
