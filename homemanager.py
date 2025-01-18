import config
from database import MyPostgresConnection
from elastic import es
from typing import Optional


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

    def add_new_item(self,
                     name: str,
                     brand: Optional[str],
                     model: Optional[str],
                     category: Optional[str],
                     quantity: int,
                     place: str,
                     belonging: Optional[str]):

        # returning name and quantity values
        result = self.conn.add_new_item(name, brand, model, category, quantity, place, belonging)

        if result[0] is True:
            print(f'Item {name} added successfully.')
        else:
            # increasing quantity by the specified value
            new_quantity = result[1] + quantity
            self.conn.update_cell('quantity', new_quantity, 'name', name)
            print(f"Item with this id already exists. Increased the quantity of this item by {result[1]}.")

    def update_table(self, destcol, destval, condcol, condval):
        successfully = self.conn.update_cell(destcol, destval, condcol, condval)
        if successfully:
            print(f'Successfully changed {destcol} field')
        else:
            print(f'No column with name {condcol} or {destcol} found')  # TODO возможно добавить свою функцию nosuchcolumnfound, используя dict и col_id

    def delete(self, name, was_last=False):
        self.conn.delete(name)

        if was_last:
            print(f'Deleted {name} from the table. '
                  f'Please note that this was the last one. Maybe you will have to buy a new one?')
        else:
            print(f'Successfully deleted {name} from the table')

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

    def welcome_view(self):
        self.conn.show_database()
