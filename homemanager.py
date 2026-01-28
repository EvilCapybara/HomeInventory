from api import Bot
import config
import telebot
from database import MyPostgresConnection
# from elastic import es
from typing import Optional
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

    def update_table(self, destcol, destval, condcol, condval):
        successfully = self.conn.update_cell(destcol, destval, condcol, condval)
        if successfully:
            print(f'Successfully changed {destcol} field')
        else:
            print(f'No column with name {condcol} or {destcol} found')  # TODO возможно добавить свою функцию nosuchcolumnfound, используя dict и col_id

    def handle_delete(self, name):
        exists, was_last = self.conn.delete(name)

        if not exists:
            text = f"Item {name} doesn't exist."

        if was_last:
            text = f"""Deleted {name} from the table.\n
                  Please note that this was the last one. Maybe you will have to buy a new one?'
                  """
        else:
            text = f'Successfully deleted {name} from the table'

    def remove(self, name, quantity):
        cur_quantity = self.conn.remove(name, quantity)
        new_quantity = cur_quantity - quantity

        if new_quantity <= 0:
            self.delete(name, was_last=True)
        else:
            self.update_table('quantity', new_quantity, 'name', name)

    def add_new_col(self, name, coltype, constraints):
        name = name.replace(' ', '_')
        coltype = type_mapping[coltype]
        if constraints == 'unique':
            raise ValueError("You cannot use UNIQUE constraint for new added column due to default value reasons.")
        elif constraints is None:
            constraints = ''
        self.conn.add_new_col(name, coltype, constraints)

        print(f'Successfully added new {name} field')

    def delete_col(self, name):
        name = name.replace(' ', '_')
        successfully = self.conn.delete_col(name)
        if successfully:
            print(f'Successfully deleted {name} field')
        else:
            print(f'No column with name {name} found')

    def rename_col(self, old_name, new_name):
        self.conn.rename_col(old_name, new_name)

        print(f'Successfully renamed {old_name} field to {new_name}')

    def find(self, colname, value):
        colname = colname.replace(' ', '_')
        target_rows = self.conn.find(colname, value)
        if target_rows:
            for row in target_rows:
                print(row)
        else:
            print(f'Item with {colname} {value} not found')



