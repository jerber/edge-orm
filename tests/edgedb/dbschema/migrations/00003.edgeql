CREATE MIGRATION m1qkgjfka2urun5x7dhfrgok7i7ouizbhxfoxmo6th6z6i4kxthfka
    ONTO m1s2qcztqtb6d35amxfaumd2bxnjezefwggqmiishzjkjs4bgay2hq
{
  ALTER TYPE default::User {
      CREATE MULTI LINK friends -> default::User {
          ON TARGET DELETE ALLOW;
      };
  };
};
