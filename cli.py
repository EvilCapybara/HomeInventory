import click
from homemanager import HomeManager


@click.group()
def adding():
    """A custom CLI tool for adding new records to the table."""
    pass


@adding.command()
@click.argument('name', type=str)
@click.argument('place', type=str)
@click.option('--quantity', type=int, help='Quantity of items', default=1)
@click.option('--category', type=str, help="Item's category", default='Unknown')
def add(name, place, quantity, category):
    home_manager = HomeManager()
    home_manager.add_new_item(values=(name, place, quantity, category))


# adding_commands.add_command(add)


# @click.group()
# def searching_commands():
#     """A custom CLI tool for searching for desired records in the table."""
#     pass




