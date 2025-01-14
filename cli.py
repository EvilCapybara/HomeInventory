import click
from typing import Optional
from homemanager import HomeManager


# @click.group()
# def change():
#     """A custom CLI tool for changing some records in the table."""
#     pass


@click.command()
@click.argument('name', type=str)
@click.argument('place', type=str)
@click.option('--quantity', type=int, help='Quantity of items', default=1)
@click.option('--category', type=str, help="Item's category", default='Unknown')
def add(name, place, quantity, category):
    home_manager = HomeManager()
    home_manager.add_new_item(values=(name, place, quantity, category))


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
@click.argument('type', type=str)
@click.option('--constraints', type=Optional[str])
def add_new_col(name, type, constraints):
    home_manager = HomeManager()
    home_manager.add_new_col(name, type, constraints)


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




