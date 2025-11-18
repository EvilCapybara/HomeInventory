from elasticsearch import Elasticsearch
from config import ELASTICSEARCH_URL

es = Elasticsearch(hosts=ELASTICSEARCH_URL)


def add_to_index(index, item):
    if not es:
        return
    payload = {}
    for col in item.__searchable__:
        payload[col] = str(getattr(item, col))
    # id_value = getattr(item, 'id')
    a = item.id
    es.index(index=index, id=item.id, document=payload)  # документ - одна запись из таблицы
    response = es.get(index=index, id=item.id)
    print(response['_source'])


def remove_from_index(index, item):
    if not es:
        return
    es.delete(index=index, id=item.id)


def query_index(index, expression):  # TODO добавить пагинацию
    if not es:
        return [], 0
    response = es.search(
        index=index,
        query={'multi_match': {'query': expression, 'fields': ['*']}})

    # каждый hit - это словарь с инфой о том, в каком документе найдено совпадение и насколько оно полное
    resulting_ids = [int(hit['_id']) for hit in response['hits']['hits']]  # list comprehension
    return resulting_ids, response['hits']['total']['value']


def delete_index(index):
    if not es:
        return
    es.indices.delete(index=index)

