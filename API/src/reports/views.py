from flask import request, make_response, jsonify

from src import DataView, api, db
from .resources import ReportResource


# @api.register()
class ReportView(DataView):
    @classmethod
    def get_resource(cls):
        return ReportResource

    def get(self, slug=None):
        return make_response(jsonify(), 200)

