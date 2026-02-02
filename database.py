''' Управление основными CRUD-операциями (create-read-update-delete) '''
# В ПОСЛЕДНЕЙ ГЛАВЕ ХАБРОВСКОГО УЧЕБННИКА ПОКАЗАНО КАК ДОБАВИТЬ БАЗОВЫЕ ОПЦИИ ДЛЯ API (РЕГИСТРАЦИЯ НОВОГО ЮЗЕРА, ВЫВОД В ФОРМАТЕ СЛОВАРЯ)

import psycopg2 as pg_driver
import sqlalchemy
from sqlalchemy import create_engine, select, delete, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, NoSuchColumnError, StatementError, ProgrammingError
from typing import Union, Optional
from models import (Base, AllHouseholdItems, Users, Task,
                    # listening
                    )
import config
import telebot.types as telebot
import elastic

TABLENAME = AllHouseholdItems.__tablename__


class MyPostgresConnection:
    def __init__(self):
        self.engine = None  # маленькая буква - атрибут класса как просто переменная
        self.session = None  # большая буква - атрибут класса как экземпляр другого класса
        self.inspector = None

    def connect(self):
        # аналог self.connection = pg_driver.connect()
        self.engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
                                    # echo=True)

        # connecting AllHouseholdItems to postgres server
        Base.metadata.create_all(self.engine)

        SessionFactory = sessionmaker(bind=self.engine)  # бол. буква - создание не объекта, а фабрики объектов
        # аналог self.cur = self.connection.cursor()
        self.session = SessionFactory()
        self.inspector = inspect(self.engine)
        # listening(self.session)

    def get_current_db_user(self, tg_user):
        """Возвращает текущий объект Users из базы по telegram_id"""
        return self.session.query(Users).filter(Users.telegram_id == tg_user.id).one_or_none()

    def can_edit_col(self, col_name: str) -> tuple[bool, str | None]:

        pk_columns = self.inspector.get_pk_constraint(TABLENAME)['constrained_columns']
        if col_name in pk_columns:
            return False, "PRIMARY KEY"

        # --- Проверка FK ---
        fks = self.inspector.get_foreign_keys(TABLENAME)
        for fk in fks:
            if col_name in fk['constrained_columns']:
                return False, "FOREIGN KEY"

        return True, None

    def show_database(self, belonging_to: int):  #TODO добавить проверку на existing юзера, чтоб каждый раз не прописывать первый блок
        ''' Just showing main table containing all household items. '''

        user = self.session.query(Users).filter_by(telegram_id=belonging_to).first()
        if not user:
            return 'no_user', None

        items = user.items

        if not items:
            return 'no_items', None

        return 'success', items

    def add_new_user(self, id, username, first_name):
        ''' Adding new record to the main table. '''

        new_user = Users(telegram_id=id, username=username, first_name=first_name)
        # print(repr(new_user))
        self.session.add(new_user)

        try:
            self.session.commit()
            # self.session.close()
            return True
        except IntegrityError as e:
            self.session.rollback()
            return False

    def export_database(self):
        if Task.get_specific_task_in_progress(name='export_inventory_table'):
            print('An export task is currently in progress')
        else:
            Task.launch_task(name='export_inventory_table', description='Exporting inventory table')
            self.session.commit()

    def add_new_item(self, user: telebot.User, item_data: dict):  # TODO вопрос добавление существующего это расчет или ошибка
        ''' Adding new record to the main table. '''

        db_user = (self.session.query(Users).filter(Users.telegram_id == user.id).one())

        new_item = AllHouseholdItems(name=item_data['name'], brand=item_data['brand'], model=item_data['model'],
                                     category=item_data['category'], quantity=item_data['quantity'],
                                     storage_place=item_data['storage_place'], belong_to=item_data['belong_to'],
                                     owner=db_user)
        # print(repr(new_item))
        self.session.add(new_item)

        try:
            self.session.commit()
            result = True
            how_many_already_existed = 0
            # self.session.close()
        except IntegrityError as e:  # TODO добавить обратную связь для юзера если данные не подходят под условия табл
            print(e)
            # logging.error(f"IntegrityError caught: {e}")
            self.session.rollback()

        query = select(AllHouseholdItems.quantity).where(AllHouseholdItems.name == item_data['name'])
        old_quantity = self.session.execute(query).scalar()
        if old_quantity is None:
            old_quantity = 0
            result = False
            how_many_already_existed = old_quantity

        return result, how_many_already_existed

    def update_cell(self, dest_column: str, dest_value: Union[str, int], cond_column: str, cond_value: Union[str, int]):
        ''' Updating cell's value in the main table. '''
        try:
            filtered_query = self.session.query(AllHouseholdItems).filter(getattr(AllHouseholdItems, cond_column) == cond_value)
            filtered_query.update({getattr(AllHouseholdItems, dest_column): dest_value})
            self.session.commit()
            return True, None
        except (IntegrityError, StatementError) as e:
            self.session.rollback()
            return False, e

    def delete(self, name: str) -> bool:
        ''' Deleting all info about specified item from the main table. '''

        item = self.session.query(AllHouseholdItems).filter(AllHouseholdItems.name == name).one_or_none()

        if not item:  # TODO сделать это отдельной функцией проверки экзиста предмета
            return False
        else:
            self.session.delete(item)
            self.session.commit()
            return True

    def remove(self, name: str) -> Optional[int]:  # TODO сделать эту функцию не как delete а просто фильтр из таблицы - ничего особенно делитного она не делает
        ''' Decreasing amount of specified items. '''

        quantity = self.session.execute(select(AllHouseholdItems.quantity).where(AllHouseholdItems.name == name))

        return quantity.scalar()

    def add_new_col(self, name: str, coltype: str, constraints: str) -> bool:
        ''' Adding new field into the main table '''
        try:
            self.session.execute(text(f'ALTER TABLE "{TABLENAME}" ADD COLUMN {name} {coltype} {constraints} DEFAULT NULL'))  # TODO потом заменить на alembic
            self.session.commit()
            return True
        except ProgrammingError as e:
            # вытаскиваем оригинальный объект ошибки драйвера psycopg2.errors.DuplicateColumn, а из него код ошибки postgres
            if getattr(e.orig, 'pgcode', None) == '42701':
                self.session.rollback()
                return False
            else:
                raise

    def delete_col(self, name: str) -> tuple[bool, str | None]:  # TODO потом заменить на alembic
        ''' Deleting the field from the main table '''

        try:
            result, reason = self.can_edit_col(col_name=name)
            if not result:
                return result, reason
            else:
                self.session.execute(text(f'ALTER TABLE "{TABLENAME}" DROP COLUMN {name}'))
                self.session.commit()
                return True, None
        except ProgrammingError as e:
            error_code = getattr(e.orig, 'pgcode', None)
            self.session.rollback()
            return False, error_code

    def rename_col(self, old_name: str, new_name: str) -> tuple[bool, str | None]:  # TODO потом заменить на alembic
        ''' Changing the field's name in the main table '''

        try:
            result, reason = self.can_edit_col(col_name=old_name)
            if not result:
                return result, reason
            else:
                self.session.execute(text(f'ALTER TABLE "{TABLENAME}" RENAME COLUMN {old_name} TO {new_name}'))
                self.session.commit()
                return True, None
        except ProgrammingError as e:
            error_code = getattr(e.orig, 'pgcode', None)
            self.session.rollback()
            return False, error_code

    def find(self, colname: str, value: Union[str, int]):
        ''' Searching for the desired item in the main table '''

        query = f"SELECT * FROM {TABLENAME} WHERE {colname} = '{value}'"
        self.cur.execute(query)
        rows = self.cur.fetchall()

        return rows if rows else False


















