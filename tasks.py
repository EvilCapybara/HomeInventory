from config import REDIS_URL
import csv
# from models import AllHouseholdItems
from notifications import send_email
import os
import redis
import rq
from sqlalchemy import select
import tempfile
import time


redis_conn = redis.Redis.from_url(REDIS_URL)
task_queue = rq.Queue('homeinventory-tasks', connection=redis_conn)


def _set_task_progress(progress):
    from models import Task
    job = rq.get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        # task = session.get(Task, job.get_id())
        task = Task.query.get(job.get_id())
        task.add_notification('task_progress', {'task_id': job.get_id(),
                                                     'progress': progress})
        if progress >= 100:
            task.complete = True
        # session.commit()


def export_inventory_table():
    try:
        _set_task_progress(0)

        # Получаем все строки
        query = select(AllHouseholdItems).order_by(AllHouseholdItems.name.asc())
        items = session.scalars(query).all()
        total = len(items)

        # Временный CSV-файл
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, newline='', suffix='.csv') as csvfile:
            fieldnames = [
                'id', 'name', 'brand', 'model',
                'category', 'quantity',
                'storage_place', 'belong_to',
                'timestamp'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for i, item in enumerate(items, start=1):
                writer.writerow({
                    'name': item.name,
                    'brand': item.brand or '',
                    'model': item.model or '',
                    'category': item.category or '',
                    'quantity': item.quantity,
                    'storage_place': item.storage_place,
                    'belong_to': item.belong_to or '',
                    'timestamp': item.timestamp.strftime('%d-%m-%y')
                })
                _set_task_progress(100 * i // total)
                time.sleep(0.2)  # имитируем долгую задачу

            temp_path = csvfile.name  #TODO добавить возможность отправлять несколько файлов

            # Отправка письма
            send_email(
                subject="Your Home Inventory list",
                text_body="Table containing all info about your household items is attached",
                attachments=temp_path,
                sync=True
            )

    except Exception:
        # logger.error('Unhandled exception', exc_info=sys.exc_info())  TODO добавить логгинг ошибок в журнал
        pass
    finally:
        _set_task_progress(100)
        os.remove(temp_path)
