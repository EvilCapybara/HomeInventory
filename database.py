import psycopg2 as pg_driver
from typing import Union


class MyPostgresConnection:
    def __init__(self, db_name: str, user: str, password: str, host: str, port: int):
        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    def connect(self):
        self.connection = pg_driver.connect(dbname=self.db_name, user=self.user, password=self.password, host=self.host,
                                            port=self.port)
        self.cur = self.connection.cursor()

    def show_database(self):
        ''' Just showing main table containing all household items. '''

        tablename = "AllHouseholdItems"
        query = f'SELECT * FROM {tablename}'
        self.cur.execute(query)
        for row in self.cur.fetchall():
            print(row)

    def create_main_table(self):
        ''' Main table containing all household items. '''

        query = '''
            CREATE TABLE IF NOT EXISTS AllHouseholdItems(
                id SERIAL PRIMARY KEY,
                category TEXT,
                name TEXT UNIQUE,
                quantity SMALLINT,
                storage_place TEXT
            )
        '''
        self.cur.execute(query)
        self.connection.commit()

    def add_new_item(self, values: tuple):
        ''' Adding new record to the main table. '''

        tablename = "AllHouseholdItems"
        query = (f'INSERT INTO {tablename} (name, storage_place, quantity, category) VALUES (%s, %s, %s, %s) '
                 f'ON CONFLICT (name) DO NOTHING')
        self.cur.execute(query, values)

        if self.cur.rowcount == 0:
            self.cur.execute(f"SELECT quantity FROM {tablename} WHERE name = '{values[0]}'")
            old_quantity = self.cur.fetchone()[0]
            return values[0], old_quantity
        else:
            self.connection.commit()
            return None

    def update_cell(self, dest_column: str, dest_value: Union[str, int], cond_column: str, cond_value: Union[str, int]):
        ''' Updating cell's value in the main table. '''

        tablename = "AllHouseholdItems"
        query = f"UPDATE {tablename} SET {dest_column} = {dest_value} WHERE {cond_column} = '{cond_value}'"
        self.cur.execute(query)
        self.connection.commit()

    def find(self, item_name: str):
        ''' Finding the desired record in the main table. '''

        tablename = "AllHouseholdItems"
        query = f'SELECT * FROM {tablename} WHERE name = {item_name}'
        self.cur.execute(query)