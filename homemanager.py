import logging
from api import Bot
import config
import telebot
from database import MyPostgresConnection
from models import AllHouseholdItems, Users
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy import select, or_
from typing import Optional, Union
import elastic
import cache

logger = logging.getLogger(__name__)

type_mapping = {'text': 'text',
                'int': 'integer',
                'float': 'float',
                'bool': 'boolean',
                'datetime.date': 'date',
                'none': 'null'
                }

PROTECTED_COLS = {"id", "name", "brand", "model", "category", "quantity", "storage_place", "belong_to", "timestamp", "owner_id"}


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
        ''' Manages all household items. '''
        self.conn = MyPostgresConnection()
        self.conn.connect()

        # Create ES index and reindex if empty (no-op when ES is unavailable)
        elastic.create_index()
        if elastic.index_is_empty():
            elastic.reindex_all(self.conn.session)

    def list_custom_cols(self) -> list[str]:
        cols = self.conn.list_cols()
        return [c for c in cols if c not in PROTECTED_COLS]

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

    def view(self, user_id: int):
        status, items = self.conn.show_database(belonging_to=user_id)

        if status == 'no_user':
            text = 'Вы ещё не зарегистрированы'
        elif status == 'no_items':
            text = 'У вас пока нет сохранённых предметов.'
        elif items:
            text_lines = []
            for item in items:
                line = f"- {item.name} | {item.quantity or '-'} | хранение: {item.storage_place}"
                text_lines.append(line)
            text = "\n".join(text_lines)
        return text

    def add_new_item(self, user_id: int, item_data: dict):
        result, how_many_already_existed = self.conn.add_new_item(user_id, item_data)

        if result is True:
            text = f"Item {item_data['name']} added successfully."
            # Sync new item to Elasticsearch and clear user's search cache
            item = self.conn.session.query(AllHouseholdItems).filter_by(name=item_data['name']).one_or_none()
            if item:
                elastic.add_to_index(item)
            cache.invalidate_user_cache(user_id)
        else:
            new_quantity = how_many_already_existed + item_data['quantity']
            self.conn.update_cell('quantity', new_quantity, 'name', item_data['name'])
            text = f"Item with this id already exists. Increased the quantity of this item by {item_data['quantity']}."
            cache.invalidate_user_cache(user_id)

        return text

    def update_table(self, destcol: str, destval: Union[str, int], condcol: str, condval: Union[str, int]):
        success, exception = self.conn.update_cell(destcol, destval, condcol, condval)
        if success:
            text = f'Successfully changed {destcol} field'
            # Invalidate cache for the owner of the updated item so next search is fresh
            item = self.conn.session.query(AllHouseholdItems).filter(
                getattr(AllHouseholdItems, condcol) == condval
            ).one_or_none()
            if item:
                elastic.add_to_index(item)
                cache.invalidate_user_cache(item.owner.telegram_id)
        elif isinstance(exception, IntegrityError):
            text = f'No column with name {condcol} or {destcol} found'
        elif isinstance(exception, StatementError):
            text = f'Wrong type of value entered for {destcol}'

        return text

    def delete(self, item_data: dict) -> str:
        # Fetch item before deletion so we have its id and owner
        item = self.conn.session.query(AllHouseholdItems).filter_by(name=item_data["name"]).one_or_none()
        item_id = item.id if item else None
        owner_telegram_id = item.owner.telegram_id if item else None

        exists = self.conn.delete(item_data["name"])

        if not exists:
            text = f"Item {item_data['name']} doesn't exist."
        else:
            text = f"Successfully deleted {item_data['name']} from the table"
            if item_id is not None:
                elastic.remove_from_index(item_id)
            if owner_telegram_id is not None:
                cache.invalidate_user_cache(owner_telegram_id)

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
        name: str = item_data["field"]["label"]
        coltype: str = item_data["field"]["type"]
        constraints: dict = item_data["field"]["constraints"]

        name = '_'.join(name.strip().lower().split())
        coltype = type_mapping[coltype]

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
        elif error_code == '42703':
            text = f'No column with name {name} found'
        elif error_code == '23503':
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
        elif error_code == '42703':
            text = f'No column with name {old_name} found'
        elif error_code == '42701':
            text = f'Column with name {new_name} already exists'
        elif error_code == '2BP01' or error_code == 'FOREIGN KEY':
            text = f'Эту колонку переименовывать нельзя'

        return text

    def find(self, item_data: dict):
        """Existing exact-match search — unchanged for backwards compatibility."""
        colname: str = item_data["colname"]
        value: str = item_data["value"]

        colname = '_'.join(colname.strip().lower().split())

        success, rows, error_code = self.conn.find(colname, value)

        if not success:
            if error_code == '42703':
                return f'No column with name "{colname}" found'
            elif error_code == '42P01':
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

    def search(self, query: str, user_id: int) -> str:
        """Full-text search using Elasticsearch with Redis caching.

        Falls back to PostgreSQL ILIKE when Elasticsearch is unavailable.
        """
        query = query.strip()
        if not query:
            return 'Введите поисковый запрос.'

        # 1. Try Redis cache
        cached = cache.get_cached_search(user_id, query)
        if cached is not None:
            if not cached:
                return f'Ничего не найдено по запросу "{query}"'
            return '\n'.join(cached)

        # 2. Resolve internal owner_id from telegram user_id
        db_user = self.conn.session.query(Users).filter_by(telegram_id=user_id).one_or_none()
        owner_id = db_user.user_id if db_user else None

        # 3. Try Elasticsearch
        ids, total = elastic.query_index(query, owner_id=owner_id)

        if ids:
            # Fetch from PostgreSQL in relevance order
            items_by_id = {
                item.id: item
                for item in self.conn.session.query(AllHouseholdItems).filter(AllHouseholdItems.id.in_(ids))
            }
            items = [items_by_id[i] for i in ids if i in items_by_id]
        else:
            # Fallback: PostgreSQL ILIKE across searchable fields
            logger.info('[search] ES unavailable or no results — falling back to PostgreSQL ILIKE')
            pattern = f'%{query}%'
            items = self.conn.session.query(AllHouseholdItems).filter(
                AllHouseholdItems.owner_id == owner_id,
                or_(
                    AllHouseholdItems.name.ilike(pattern),
                    AllHouseholdItems.brand.ilike(pattern),
                    AllHouseholdItems.model.ilike(pattern),
                    AllHouseholdItems.category.ilike(pattern),
                    AllHouseholdItems.storage_place.ilike(pattern),
                )
            ).all()

        if not items:
            cache.set_cached_search(user_id, query, [])
            return f'Ничего не найдено по запросу "{query}"'

        lines = [
            f"- {item.name} | {item.quantity or '-'} | хранение: {item.storage_place}"
            for item in items
        ]
        cache.set_cached_search(user_id, query, lines)
        return '\n'.join(lines)
