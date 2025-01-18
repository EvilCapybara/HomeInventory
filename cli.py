import click
from homemanager import HomeManager


# @click.group()
# def change():
#     """A custom CLI tool for changing some records in the table."""
#     pass


@click.command()
@click.argument('name', type=str)
@click.argument('place', type=str)
@click.option('--brand', type=str, help="Item's brand", default=None)
@click.option('--model', type=str, help="Item's model", default=None)
@click.option('--category', type=str, help="Item's category", default=None)
@click.option('--quantity', type=int, help='Quantity of items', default=1)
@click.option('--belonging', type=str, help="Item's owner", default=None)
def add(name, brand, model, category, quantity, place, belonging):
    home_manager = HomeManager()
    home_manager.add_new_item(name, brand, model, category, quantity, place, belonging)


@click.command()
@click.argument('destcol', type=str)
@click.argument('destval', type=str)
@click.argument('condcol', type=str)
@click.argument('condval', type=str)
def update(destcol, destval, condcol, condval):
    home_manager = HomeManager()
    home_manager.update_table(destcol, destval, condcol, condval)


@click.command()
@click.argument('name', type=str)
def delete(name):
    home_manager = HomeManager()
    home_manager.delete(name)


@click.command()
@click.argument('name', type=str)
@click.option('--quantity', type=int, default=1)
def remove(name, quantity):
    home_manager = HomeManager()
    home_manager.remove(name, quantity)


@click.command()
@click.argument('name', type=str)
@click.argument('coltype', type=str)
@click.option('--constraints', type=str)
def add_new_col(name, coltype, constraints):
    home_manager = HomeManager()
    home_manager.add_new_col(name, coltype, constraints)


@click.command()
@click.argument('name', type=str)
def delete_col(name):
    home_manager = HomeManager()
    home_manager.delete_col(name)


@click.command()
@click.argument('oldname', type=str)
@click.argument('newname', type=str)
def rename_col(oldname, newname):
    home_manager = HomeManager()
    home_manager.rename_col(oldname, newname)


# change.add_command(add)
# change.add_command(update)


# @click.group()
# def searching():
#     """A custom CLI tool for searching for desired records in the table."""
#     pass


@click.command()
@click.argument('colname', type=str)
@click.argument('value', type=str)
def find(colname, value):
    home_manager = HomeManager()
    home_manager.find(colname, value)




