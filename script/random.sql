CREATE RANDOM STREAM test_generate(
  name string default generate('name', rand()),
  location string default generate('city', rand())||to_string(rand()%10),
  temperature float default rand()%1000/10)
settings eps = 5;