from database import MyPostgresConnection
import config
from elastic import es


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
        # self.conn.create_main_table()

        # self.elasticsearch = es

    def add_new_item(self, values: tuple):  # FIXME change (values) to smth more describing
        # returning name and quantity values
        data_to_add = self.conn.add_new_item(values)

        if data_to_add is not None:  # added already existing item
            # increasing quantity by the specified value
            new_quantity = data_to_add[1] + values[2]
            self.conn.update_cell('quantity', new_quantity, 'name', data_to_add[0])
            print(f"Item with this id already exists. Increased the quantity of this item by {values[2]}.")
        else:
            print(f"New item {values[0]} was inserted successfully.")

    def update_table(self, destcol, destval, condcol, condval):
        self.conn.update_cell(destcol, destval, condcol, condval)

        print(f'Successfully changed {destcol} field')

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
            self.conn.update_cell('quantity', new_quantity, 'name', name)

    def add_new_col(self, name, type, constraints):
        name = name.replace(' ', '_')
        type = type_mapping[type]
        if constraints == 'unique':
            raise ValueError("You cannot use UNIQUE constraint for new added column due to default value reasons.")
        elif constraints is None:
            constraints = ''
        self.conn.add_new_col(name, type, constraints)

        print(f'Successfully added new {name} field')

    def delete_col(self, name):
        name = name.replace(' ', '_')
        self.conn.delete_col(name)

        print(f'Successfully deleted {name} field')

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
