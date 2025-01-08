from database import MyPostgresConnection


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
        # configuration data
        DATABASE_NAME = 'HomeInventory'
        DATABASE_USER = 'postgres'
        DATABASE_PASSWORD = '1'
        DATABASE_HOST = 'localhost'
        DATABASE_PORT = 5432

        # connecting to the database, creating its main table and filling it
        ''' Manages all household items. '''
        self.conn = MyPostgresConnection(db_name=DATABASE_NAME, user=DATABASE_USER,
                                         password=DATABASE_PASSWORD,
                                         host=DATABASE_HOST, port=DATABASE_PORT)
        self.conn.connect()
        self.conn.create_main_table()

    def add_new_item(self, values: tuple):
        # returning name and quantity values
        data_to_add = self.conn.add_new_item(values)

        if data_to_add is not None:  # added already existing item
            # increasing quantity by the specified value
            new_quantity = data_to_add[1] + values[2]
            self.conn.update_cell('quantity', new_quantity, 'name', data_to_add[0])  # TODO сделать метод update для менеджера, а не conn
            print(f"Item with this id already exists. Increased the quantity of this item by {values[2]}.")
        else:
            print(f"New item {values[0]} was inserted successfully.")

    def update_table(self, destcol, destval, condcol, condval):
        self.conn.update_cell(destcol, destval, condcol, condval)
        print(f'Successfully changed {destcol} field ')

    def welcome_view(self):
        self.conn.show_database()
