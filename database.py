import psycopg2 as pg_driver
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Union
from models import Base
import config

TABLENAME = "AllHouseholdItems"


class MyPostgresConnection:
    def __init__(self):
        # self.db_name = db_name
        # self.user = user
        # self.password = password
        # self.host = host
        # self.port = port  # маленькая буква - атрибут класса как просто переменная
        self.engine = None
        self.session = None  # большая буква - атрибут класса как экземпляр другого класса

    def connect(self):
        # аналог self.connection = pg_driver.connect()
        self.engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=True)

        # connecting AllHouseholdItems to postgres server
        Base.metadata.create_all(self.engine)

        SessionFactory = sessionmaker(bind=self.engine)  # мал. буква - создание не объекта, а фабрики объектов
        # аналог self.cur = self.connection.cursor()
        self.session = SessionFactory()

        # self.connection = pg_driver.connect(dbname=self.db_name, user=self.user, password=self.password,
#                                             host=self.host, port=self.port)
#         self.cur = self.connection.cursor()

    def show_database(self):
        ''' Just showing main table containing all household items. '''

        query = f'SELECT * FROM {TABLENAME} ORDER BY id'
        self.cur.execute(query)
        for row in self.cur.fetchall():
            print(row)

    def create_main_table(self):
        ''' Main table containing all household items. '''

        # query = '''
        #     CREATE TABLE IF NOT EXISTS AllHouseholdItems(
        #         id SERIAL PRIMARY KEY,
        #         category TEXT,
        #         name TEXT NOT NULL,
        #         quantity SMALLINT,
        #         storage_place TEXT NOT NULL
        #     )
        # '''
        # self.cur.execute(query)
        # self.connection.commit()

    def add_new_item(self, values: tuple):
        ''' Adding new record to the main table. '''

        query = (f'INSERT INTO {TABLENAME} (name, storageplace, quantity, category) VALUES (%s, %s, %s, %s) '
                 f'ON CONFLICT (name) DO NOTHING')
        self.cur.execute(query, values)

        if self.cur.rowcount == 0:
            self.cur.execute(f"SELECT quantity FROM {TABLENAME} WHERE name = '{values[0]}'")
            old_quantity = self.cur.fetchone()[0]
            return values[0], old_quantity
        else:
            self.connection.commit()
            return None

    def update_cell(self, dest_column: str, dest_value: Union[str, int], cond_column: str, cond_value: Union[str, int]):
        ''' Updating cell's value in the main table. '''

        query = f"UPDATE {TABLENAME} SET {dest_column} = '{dest_value}' WHERE {cond_column} = '{cond_value}'"
        self.cur.execute(query)
        self.connection.commit()

    def delete(self, name: str):
        ''' Deleting all info about specified item from the main table. '''

        self.cur.execute(f"DELETE FROM {TABLENAME} WHERE name = '{name}'")
        self.connection.commit()

    def remove(self, name: str, quantity: int):
        ''' Decreasing amount of specified items. '''

        self.cur.execute(f"SELECT quantity FROM {TABLENAME} WHERE name = '{name}'")

        return self.cur.fetchone()[0]

    def add_new_col(self, name: str, type: str, constraints: str):
        ''' Adding new field into the main table '''

        self.cur.execute(f"ALTER TABLE {TABLENAME} ADD COLUMN {name} {type} {constraints} DEFAULT 'unknown'")
        self.connection.commit()

    def delete_col(self, name: str):
        ''' Deleting the field from the main table '''

        self.cur.execute(f'ALTER TABLE {TABLENAME} DROP COLUMN {name}')
        self.connection.commit()

    def rename_col(self, old_name: str, new_name: str):
        ''' Changing the field's name in the main table '''

        self.cur.execute(f'ALTER TABLE {TABLENAME} RENAME COLUMN {old_name} TO {new_name}')
        self.connection.commit()

    def find(self, colname: str, value: Union[str, int]):
        ''' Searching for the desired item in the main table '''

        query = f"SELECT * FROM {TABLENAME} WHERE {colname} = '{value}'"
        self.cur.execute(query)
        rows = self.cur.fetchall()

        return rows if rows else False


















