CREATE MIGRATION m1iwiyzqeivso5aqne2m7cm7npdf4uvgp6qntaacdfcebsv5dbts7a
    ONTO m1rmywqmbxxztt5me2rbmkozzrf5wczsfbjnpmgujgjnnkamqm6deq
{
  ALTER TYPE default::User {
      CREATE PROPERTY email -> std::str;
  };
};
