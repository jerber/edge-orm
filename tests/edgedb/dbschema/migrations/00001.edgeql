CREATE MIGRATION m1bn5mlg3vhwtcplviqupzosfxxleb74koeimvf7ylk7abok2c3zkq
    ONTO initial
{
  CREATE TYPE default::User {
      CREATE REQUIRED PROPERTY name -> std::str;
      CREATE REQUIRED PROPERTY phone_number -> std::str {
          SET readonly := true;
          CREATE CONSTRAINT std::exclusive;
      };
  };
};
