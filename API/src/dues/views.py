from src import BaseView
from src import api
from src.utils.methods import List, Fetch, Create, Update
from .resources import DueResource, PaymentResource

@api.register()
class DueView(BaseView):
    api_methods = [List, Fetch, Create, Update]

    @classmethod
    def get_resource(cls):
        return DueResource


@api.register()
class PaymentView(BaseView):
    api_methods = [List, Fetch]

    @classmethod
    def get_resource(cls):
        return PaymentResource
