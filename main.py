''' Точка входа в программу '''

import logging

import cli
from homemanager import HomeManager


def main():
    ''' Main function. '''

    home_manager = HomeManager()
    # cli.delete()
    # home_manager.welcome_view()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        raise
