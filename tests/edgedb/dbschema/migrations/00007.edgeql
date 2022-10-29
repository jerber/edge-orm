CREATE MIGRATION m1rmywqmbxxztt5me2rbmkozzrf5wczsfbjnpmgujgjnnkamqm6deq
    ONTO m1ul2klowp7cutdodpxieur2pkotdb4gz36vgtqbnz3tecokwc3dla
{
  ALTER TYPE default::User {
      CREATE PROPERTY images -> array<std::json>;
  };
};
