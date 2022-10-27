CREATE MIGRATION m1lddio2htrzjhtc3k7mynk7qdjcezmip5y4uv3aawas32grxkl2sq
    ONTO m1qkgjfka2urun5x7dhfrgok7i7ouizbhxfoxmo6th6z6i4kxthfka
{
  ALTER TYPE default::User {
      CREATE PROPERTY names_of_friends := (.friends.name);
  };
};
