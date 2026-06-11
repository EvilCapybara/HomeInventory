import logging
from elasticsearch import Elasticsearch, NotFoundError
from config import ELASTICSEARCH_URL

logger = logging.getLogger(__name__)

INDEX = 'household_items'
SEARCH_FIELDS = ['name', 'brand', 'model', 'category', 'storage_place']

es = Elasticsearch(hosts=ELASTICSEARCH_URL) if ELASTICSEARCH_URL else None


def create_index():
    if not es:
        return
    try:
        if es.indices.exists(index=INDEX):
            return
        es.indices.create(index=INDEX, mappings={
            'properties': {
                'name':          {'type': 'text'},
                'brand':         {'type': 'text'},
                'model':         {'type': 'text'},
                'category':      {'type': 'text'},
                'storage_place': {'type': 'text'},
                'owner_id':      {'type': 'integer'},
            }
        })
        logger.info('Elasticsearch index "%s" created.', INDEX)
    except Exception as e:
        logger.warning('Could not create ES index: %s', e)


def add_to_index(item):
    if not es:
        return
    try:
        doc = {field: str(getattr(item, field) or '') for field in SEARCH_FIELDS}
        doc['owner_id'] = item.owner_id
        es.index(index=INDEX, id=item.id, document=doc)
    except Exception as e:
        logger.warning('ES add_to_index failed for item %s: %s', item.id, e)


def remove_from_index(item_id: int):
    if not es:
        return
    try:
        es.delete(index=INDEX, id=item_id)
    except NotFoundError:
        pass
    except Exception as e:
        logger.warning('ES remove_from_index failed for id %s: %s', item_id, e)


def query_index(expression: str, owner_id: int = None):
    """Return (list_of_item_ids, total_count) ranked by relevance."""
    if not es:
        return [], 0
    try:
        base_query = {
            'multi_match': {
                'query': expression,
                'fields': SEARCH_FIELDS,
                'fuzziness': 'AUTO',
            }
        }
        if owner_id is not None:
            query = {
                'bool': {
                    'must': base_query,
                    'filter': {'term': {'owner_id': owner_id}},
                }
            }
        else:
            query = base_query

        response = es.search(index=INDEX, query=query, size=20)
        ids = [int(hit['_id']) for hit in response['hits']['hits']]
        total = response['hits']['total']['value']
        return ids, total
    except Exception as e:
        logger.warning('ES query_index failed: %s', e)
        return [], 0


def reindex_all(session):
    """Full reindex of all items from PostgreSQL. Safe to call at startup."""
    if not es:
        return
    try:
        from models import AllHouseholdItems
        from sqlalchemy import select
        create_index()
        count = 0
        for item in session.scalars(select(AllHouseholdItems)):
            add_to_index(item)
            count += 1
        logger.info('Reindexed %d items into Elasticsearch.', count)
    except Exception as e:
        logger.warning('reindex_all failed: %s', e)


def index_is_empty() -> bool:
    """Return True if the ES index has no documents (or ES is unavailable)."""
    if not es:
        return False
    try:
        create_index()
        response = es.count(index=INDEX)
        return response['count'] == 0
    except Exception:
        return False
