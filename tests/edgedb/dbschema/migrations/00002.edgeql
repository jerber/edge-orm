CREATE MIGRATION m1s2qcztqtb6d35amxfaumd2bxnjezefwggqmiishzjkjs4bgay2hq
    ONTO m1bn5mlg3vhwtcplviqupzosfxxleb74koeimvf7ylk7abok2c3zkq
{
  ALTER TYPE default::User {
      CREATE PROPERTY age -> std::int16;
  };
};
