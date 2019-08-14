from datetime import datetime
from typing import List

from src import celery, sms, db


@celery.task(acks_late=True)
def check_integration() -> bool:

    db.session.commit()
    return True
