from flask import request
from flask_security import current_user
from sqlalchemy import and_

from src.utils import DataResource, operators as ops


class ReportResource(DataResource):

    max_limit: int = 1000

    default_limit: int = 1000

    page: int = 1

    auth_required: bool = True

    export: bool = True

    max_export_limit: int = 5000

    roles_accepted = ('admin', 'owner', 'manager', 'order_taker')

    headers = [('parent_category_name', 'name', 'quantity', 'rate', 'net_price', 'discount', 'total_tax',
                'gross_price', 'outlet')]

    def construct_query_set(self):
        return self.model.query