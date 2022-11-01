CREATE MIGRATION m16mvwzegsftyz43iv6dxwldsv7snry4kclnmujezeodko2ici6zea
    ONTO m1iwiyzqeivso5aqne2m7cm7npdf4uvgp6qntaacdfcebsv5dbts7a
{
  ALTER TYPE default::User {
      CREATE PROPERTY ids_of_friends := (.friends.id);
  };
};
