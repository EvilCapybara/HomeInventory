import click
from typing import Union
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


# change.add_command(add)
# change.add_command(update)


# @click.group()
# def searching_commands():
#     """A custom CLI tool for searching for desired records in the table."""
#     pass




