import psycopg2 as pg_driver
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from typing import Union
from models import Base, AllHouseholdItems
import config
import logging

TABLENAME = "AllHouseholdItems"


class MyPostgresConnection:
    def __init__(self):
        self.engine = None  # маленькая буква - атрибут класса как просто переменная
        self.session = None  # большая буква - атрибут класса как экземпляр другого класса

    def connect(self):
        # аналог self.connection = pg_driver.connect()
        self.engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
                                    # echo=True)

        # connecting AllHouseholdItems to postgres server
        Base.metadata.create_all(self.engine)

        SessionFactory = sessionmaker(bind=self.engine)  # мал. буква - создание не объекта, а фабрики объектов
        # аналог self.cur = self.connection.cursor()
        self.session = SessionFactory()
        # my_table = Base.metadata.tables['AllHouseholdItems']
        # print(my_table.__repr__())

    def show_database(self):
        ''' Just showing main table containing all household items. '''

        query = f'SELECT * FROM {TABLENAME} ORDER BY id'
        self.cur.execute(query)
        for row in self.cur.fetchall():
            print(row)

    def add_new_item(self, name, brand, model, category, quantity, place, belonging):  # TODO вопрос добавление существующего это расчет или ошибка
        ''' Adding new record to the main table. '''

        new_item = AllHouseholdItems(name=name, brand=brand, model=model, category=category, quantity=quantity,
                                     storage_place=place, belong_to=belonging)
        self.session.add(new_item)

        try:
            self.session.commit()
            # self.session.close()
            return True, None
        except IntegrityError as e:
            # logging.error(f"IntegrityError caught: {e}")
            self.session.rollback()

            query = select(AllHouseholdItems.quantity).where(AllHouseholdItems.name == name)
            old_quantity = self.session.execute(query).scalar()
            return False, old_quantity

    def update_cell(self, dest_column: str, dest_value: Union[str, int], cond_column: str, cond_value: Union[str, int]):
        ''' Updating cell's value in the main table. '''

        # cond_column = getattr(AllHouseholdItems, cond_column)
        filtered_query = self.session.query(AllHouseholdItems).filter(getattr(AllHouseholdItems, cond_column) == cond_value)
        # dest_column = getattr(AllHouseholdItems, dest_column)
        filtered_query.update({getattr(AllHouseholdItems, dest_column): dest_value})
        self.session.commit()

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


















