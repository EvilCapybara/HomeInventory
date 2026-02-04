from api import Bot
import config
import telebot
from database import MyPostgresConnection
from sqlalchemy.exc import IntegrityError, StatementError
# from elastic import es
from typing import Optional, Union
# from models import SearchableMixin


type_mapping = {'str': 'text',
                'int': 'integer',
                'float': 'float',
                'bool': 'boolean',
                'datetime.date': 'date',
                'none': 'null'
                }


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


@singleton
class HomeManager:
    def __init__(self):
        # connecting to the database, creating its main table and filling it
        ''' Manages all household items. '''
        # self.conn = MyPostgresConnection(db_name=config.DATABASE_NAME, user=config.DATABASE_USER,
        #                                  password=config.DATABASE_PASSWORD,
        #                                  host=config.DATABASE_HOST, port=config.DATABASE_PORT)
        self.conn = MyPostgresConnection()
        self.conn.connect()

        # self.elasticsearch = es
        # result, total = SearchableMixin.search("sony", connection=self.conn)
        # SearchableMixin.reindex(connection=self.conn)

    # def add_new_user(self, username, first_name):
    #
    #     result = self.conn.add_new_user(username, first_name)
    #
    #     if result is True:
    #         print(f'User {username} added successfully.')
    #     else:
    #         print(f"User with this username already exists.")
    #         return False

    def handle_start(self, user: telebot.types.User):
        if self.conn.add_new_user(user.id, user.username, user.first_name):
            text = f"""Привет, *{user.first_name}*!\n"
                   Я бот-помощник. Помогу вести подробный учет твоего домашнего пространства.\n
                   Чтобы начать или продолжить наполнение своего виртуального домика, отправь команду /add new item.\n
                   Чтобы просмотреть все добавленные предметы - /show_my_household
                   Для отмены – /cancel.\n
                   Эффективной организации!
                   """
            return text
        text = 'Вы уже зарегистрированы!'
        return text

    def handle_view(self, user: telebot.types.User):
        # self.conn.show_database()
        status, items = self.conn.show_database(belonging_to=user.id)  # убрать прокидывание юзера через вызовы, пусть каждый раз вычисляется в database
        if status == 'no_user':
            text = 'Вы ещё не зарегистрированы'
        elif status == 'no_items':
            text = 'У вас пока нет сохранённых предметов.'
        else:
            return
        if items:
            text_lines = []
            for item in items:
                line = f"- {item.name} | {item.quantity or '-'} | хранение: {item.storage_place}"
                text_lines.append(line)
            text = "\n".join(text_lines)
        return text

    def add_new_item(self, user, item_data: dict):

        # returning name and quantity values
        result, how_many_already_existed = self.conn.add_new_item(user, item_data)

        if result is True:
            text = f"Item {item_data['name']} added successfully."
        else:
            # increasing quantity by the specified value
            new_quantity = how_many_already_existed + item_data['quantity']
            self.conn.update_cell('quantity', new_quantity, 'name', item_data['name'])
            text = f"Item with this id already exists. Increased the quantity of this item by {item_data['quantity']}."

        return text

    def update_table(self, destcol: str, destval: Union[str, int], condcol: str, condval: Union[str, int]):
        success, exception = self.conn.update_cell(destcol, destval, condcol, condval)
        if success:
            text = f'Successfully changed {destcol} field'
        elif isinstance(exception, IntegrityError):
            text = f'No column with name {condcol} or {destcol} found'  # TODO возможно добавить свою функцию nosuchcolumnfound, используя dict и col_id
        elif isinstance(exception, StatementError):
            text = f'Wrong type of value entered for {destcol}'

        return text

    def delete(self, item_data: dict) -> str:
        exists = self.conn.delete(item_data["name"])

        if not exists:
            text = f"Item {item_data['name']} doesn't exist."
        else:
            text = f"Successfully deleted {item_data['name']} from the table"

        return text

    def edit_quantity(self, item_data: dict, context: str) -> str:
        cur_quantity = self.conn.remove(item_data["name"], item_data["quantity"])

        if context == 'remove':
            new_quantity = cur_quantity - item_data["quantity"]
        elif context == 'add_more':
            new_quantity = cur_quantity + item_data["quantity"]

        if new_quantity <= 0:
            if new_quantity == 0:
                text = f"""Deleted {item_data['name']} from the table.\n
                           Please note that this was the last one. Maybe you will have to buy a new one?
                        """
            self.handle_delete(item_data)

        elif new_quantity > 0:
            text = self.update_table('quantity', new_quantity, 'name', item_data["name"])

        return text

    def add_newcol(self, item_data: dict) -> str:
        name: str = item_data["name"]
        coltype: str = item_data["type"]
        constraints: Optional[str] = item_data["constraints"]

        name = '_'.join(name.strip().lower().split())

        coltype = type_mapping[coltype]

        # if constraints == 'unique':
        #     raise ValueError("You cannot use UNIQUE constraint for new added column due to default value reasons.")
        if constraints == '-' or constraints is None:
            constraints = ''

        if self.conn.add_new_col(name, coltype, constraints):
            text = f'Successfully added new {name} field'
        else:
            text = f'Field with name {name} already exists!'

        return text

    def delete_col(self, item_data: dict) -> str:
        name: str = item_data["name"]
        name = '_'.join(name.strip().lower().split())

        success, error_code = self.conn.delete_col(name)

        if success:
            text = f'Successfully deleted {name} field'
        elif error_code == '42703':  # undefined column
            text = f'No column with name {name} found'
        elif error_code == '23503':  # foreign key violation
            text = f'Колонку "{name}" нельзя удалить — есть зависимые FK'

        return text

    def rename_col(self, item_data: dict) -> str:
        old_name: str = item_data["old_name"]
        new_name: str = item_data["new_name"]

        old_name = '_'.join(old_name.strip().lower().split())
        new_name = '_'.join(new_name.strip().lower().split())

        success, error_code = self.conn.rename_col(old_name, new_name)

        if success:
            text = f'Successfully renamed {old_name} field to {new_name}'
        elif error_code == '42703':  # undefined column
            text = f'No column with name {old_name} found'
        elif error_code == '42701':  # column already exists
            text = f'Column with name {new_name} already exists'
        elif error_code == '2BP01' or error_code == 'FOREIGN KEY':  # foreign key constraint
            text = f'Эту колонку переименовывать нельзя'

        return text

    def find(self, item_data: dict):

        colname: str = item_data["colname"]
        value: str = item_data["value"]

        colname = '_'.join(colname.strip().lower().split())
        # value = ' '.join(value.strip().lower().split())

        success, rows, error_code = self.conn.find(colname, value)

        if not success:

            if error_code == '42703':  # undefined column
                return f'No column with name "{colname}" found'
            elif error_code == '42P01':  # undefined table
                return 'Table does not exist'
            else:
                return f'Database error ({error_code})'

        if not rows:
            return f'Item with {colname} "{value}" not found'

        text_lines = []

        for row in rows:
            line = f"- {row.name} | {row.quantity or '-'} | хранение: {row.storage_place}"
            text_lines.append(line)

        return "\n".join(text_lines)


