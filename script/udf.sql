CREATE OR REPLACE FUNCTION generate(data string, seed uint32) RETURNS string LANGUAGE PYTHON AS 
$$
from faker import Faker
fake = Faker()

def generate(data, seed):
  result = []
  for d , s in zip(data, seed):
    try:
      r = fake.format(d)
      result.append(r)
    except:
      result.append('')
  return result
$$;
