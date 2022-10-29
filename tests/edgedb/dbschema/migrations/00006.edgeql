CREATE MIGRATION m1ul2klowp7cutdodpxieur2pkotdb4gz36vgtqbnz3tecokwc3dla
    ONTO m125hw4qgsar6fzcby2l6ntghpge5c7ambllcclju3z7pjbyg3g6pa
{
  CREATE SCALAR TYPE default::UserRole EXTENDING enum<buyer, seller, admin>;
  ALTER TYPE default::User {
      CREATE PROPERTY user_role -> default::UserRole;
  };
};
