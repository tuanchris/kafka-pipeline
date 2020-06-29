from faker import Faker
import psycopg2
from time import sleep
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine

if __name__ == '__main__':
    conn = create_engine("postgresql://TEST:password@localhost/TEST") 
    faker = Faker() 
    fields = ['job','company','residence','username','name','sex','address','mail','birthdate','ssn']
    i = 0

    while True: 
        data = faker.profile(fields)
        data['timestamp'] = datetime.now()
        df = pd.DataFrame(data, index = [i])
        print(f"Inserting data {data}")
        df.to_sql('USERS',conn, if_exists='append')
        i +=1 
        sleep(1)
