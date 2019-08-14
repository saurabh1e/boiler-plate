import re
from typing import TypeVar
from abc import abstractmethod
from functools import wraps

from flask_restful import Api
from flask_restful import Resource
from flask import request, jsonify, make_response
from flask_security.decorators import _security, current_app, \
    _request_ctx_stack, identity_changed, Identity, _get_unauthorized_response
from flask_jwt_extended import jwt_required, get_jwt_identity


from flask_excel import make_response_from_records
from flask_security import roles_required, roles_accepted
from sqlalchemy.exc import DataError

from .models import db
from .blue_prints import bp
from .resource import ModelResource, AssociationModelResource, DataResource
from .exceptions import ResourceNotFound, SQLIntegrityError, SQlOperationalError, CustomException, \
    SQlInvalidRequestError, SQLDetachedInstanceError
from .methods import BulkUpdate, List, Fetch, Create, Delete, Update

ModelResourceType = TypeVar('ModelResourceType', bound=ModelResource)
AssociationModelResource = TypeVar('AssociationModelResource', bound=AssociationModelResource)
DataResourceType = TypeVar('DataResourceType', bound=DataResource)


def _check_token():
    user = _security.datastore.get_user(get_jwt_identity()['id'])
    if user and user.is_authenticated:
        app = current_app._get_current_object()
        _request_ctx_stack.top.user = user
        identity_changed.send(app, identity=Identity(user.id))
        return True

    return False


def set_user(fn):
    @wraps(fn)
    def decorated(*args, **kwargs):
        if _check_token():
            return fn(*args, **kwargs)
        if _security._unauthorized_callback:
            return _security._unauthorized_callback()
        else:
            return _get_unauthorized_response()

    return decorated


def to_underscore(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class ApiFactory(Api):
    def init_app(self, app):
        super(ApiFactory, self).init_app(app)

    def register(self, **kwargs):

        def decorator(klass):
            document_name = klass.get_resource().model.__name__.lower()
            name = kwargs.pop('name', document_name)
            url = kwargs.pop('url', '/%s' % to_underscore(klass.__name__).replace('_view', ''))
            endpoint = to_underscore(klass.__name__)
            view_func = klass.as_view(name)
            methods = klass.api_methods

            for method in methods:
                if method.slug:
                    self.app.add_url_rule(url + '/<string:slug>', endpoint=endpoint, view_func=view_func,
                                          methods=[method.method], **kwargs)
                else:
                    self.app.add_url_rule(url, endpoint=endpoint, view_func=view_func,
                                          methods=[method.method], **kwargs)
            return klass

        return decorator


api = ApiFactory(bp)


class BaseView(Resource):
    api_methods = [BulkUpdate, List, Fetch, Create, Delete, Update]

    def __init__(self):
        if self.get_resource() is not None:
            self.resource = self.get_resource()()
            self.add_method_decorator()

    @classmethod
    @abstractmethod
    def get_resource(cls) -> ModelResourceType:
        pass

    def add_method_decorator(self):
        self.method_decorators = []
        if self.resource.auth_required:
            self.method_decorators.append(roles_required(*[i for i in self.resource.roles_required]))
            self.method_decorators.append(roles_accepted(*[i for i in self.resource.roles_accepted]))
            self.method_decorators.append(set_user)
            self.method_decorators.append(jwt_required)

    def get(self, slug=None):
        if slug:
            obj = self.resource.model.query.filter(self.resource.model.id == slug)
            obj = self.resource.has_read_permission(obj).first()
            if obj:
                schema = self.resource.schema
                if self.resource.only:
                    data = schema(exclude=tuple(self.resource.obj_exclude), only=tuple(self.resource.obj_only))
                else:
                    data = schema(exclude=tuple(self.resource.obj_exclude))

                return make_response(jsonify(data.dump(obj, many=False).data), 200)

            return make_response(jsonify({'error': True, 'message': 'Resource not found'}), 404)

        else:
            objects = self.resource.apply_filters(queryset=self.resource.model.query, **request.args)
            objects = self.resource.has_read_permission(objects)

            if '__order_by' in request.args:
                objects = self.resource.apply_ordering(objects, request.args.getlist('__order_by'))

            if '__export__' in request.args and self.resource.export is True:
                objects = objects.paginate(page=self.resource.page, per_page=self.resource.max_export_limit)
                return make_response_from_records(
                    self.resource.schema(exclude=tuple(self.resource.obj_exclude), only=tuple(self.resource.obj_only))
                        .dump(objects.items, many=True).data, 'csv', 200, self.resource.model.__name__)
            try:
                resources = objects.paginate(page=self.resource.page, per_page=self.resource.limit)
            except DataError as e:
                return make_response(jsonify(dict(message='invalid query params', operation='Query Resource',
                                                  error=str(e))), 400)
            if resources.items:
                schema = self.resource.schema
                if self.resource.only:
                    data = schema(exclude=tuple(self.resource.obj_exclude), only=tuple(self.resource.obj_only))
                else:
                    data = schema(exclude=tuple(self.resource.obj_exclude))
                return make_response(jsonify({'success': True,
                                              'data': data
                                             .dump(resources.items, many=True).data, 'total': resources.total}), 200)
            return make_response(jsonify({'error': True, 'message': 'No Resource Found'}), 404)

    def post(self):
        try:
            data, status = self.resource.save_resource()
        except (SQLIntegrityError, SQlOperationalError, SQlInvalidRequestError) as e:
            db.session.rollback()
            e.message['error'] = True
            return make_response(jsonify(e.message), e.status)
        return make_response(jsonify(data), status)

    def put(self):

        try:
            data, status = self.resource.update_resource()
        except (SQLIntegrityError, SQlOperationalError, SQlInvalidRequestError) as e:
            db.session.rollback()
            e.message['error'] = True
            return make_response(jsonify(e.message), e.status)
        return make_response(jsonify(data), status)

    def patch(self, slug):
        if not db.session.query(self.resource.model.query
                                        .filter(self.resource.model.id == slug).exists()).scalar():
            return make_response(jsonify({'error': True, 'message': 'Resource not found'}), 404)
        try:
            data, status = self.resource.patch_resource(slug)
        except (SQLIntegrityError, SQlOperationalError, SQlInvalidRequestError, SQLDetachedInstanceError) as e:
            db.session.rollback()
            e.message['error'] = True
            return make_response(jsonify(e.message), e.status)
        return make_response(jsonify(data), status)

    def delete(self, slug):

        obj = self.resource.model.query.get(slug)
        if obj:
            if self.resource.has_delete_permission(obj):
                db.session.delete(obj)
                db.session.commit()
                return make_response(jsonify({'message': 'No Content'}), 204)
            else:
                return make_response(
                    jsonify({'error': True, 'message': 'Forbidden Permission Denied To Delete Resource'}), 403)
        return make_response(jsonify({'error': True, 'message': 'Resource not found'}), 404)


class AssociationView(Resource):
    api_methods = [Create, List, Fetch]

    def __init__(self):
        if self.get_resource is not None:
            self.resource = self.get_resource()()
            self.add_method_decorator()

    @abstractmethod
    def get_resource(self) -> AssociationModelResource:
        pass

    def add_method_decorator(self):
        self.method_decorators = []
        if self.resource.auth_required:
            # self.method_decorators.append(check_shop_access)
            self.method_decorators.append(roles_required(*[i for i in self.resource.roles_required]))
            self.method_decorators.append(roles_accepted(*[i for i in self.resource.roles_accepted]))
            self.method_decorators.append(jwt_required)

    def get(self, slug=None):
        if slug:
            obj = self.resource.model.query.filter(self.resource.model.id == slug)
            obj = self.resource.has_read_permission(obj).first()
            if obj:
                schema = self.resource.schema
                if self.resource.only:
                    data = schema(exclude=tuple(self.resource.obj_exclude), only=tuple(self.resource.obj_only))
                else:
                    data = schema(exclude=tuple(self.resource.obj_exclude))

                return make_response(jsonify(data.dump(obj, many=False).data), 200)

            return make_response(jsonify({'error': True, 'message': 'Resource not found'}), 404)

        else:
            objects = self.resource.apply_filters(queryset=self.resource.model.query, **request.args)
            objects = self.resource.has_read_permission(objects)

            if '__order_by' in request.args:
                objects = self.resource.apply_ordering(objects, request.args['__order_by'])
            resources = objects.paginate(page=self.resource.page, per_page=self.resource.limit)
            if resources.items:
                schema = self.resource.schema
                if self.resource.only:
                    data = schema(exclude=tuple(self.resource.obj_exclude), only=tuple(self.resource.obj_only))
                else:
                    data = schema(exclude=tuple(self.resource.obj_exclude))
                return make_response(jsonify({'success': True,
                                              'data': data
                                             .dump(resources.items, many=True).data, 'total': resources.total}), 200)
            return make_response(jsonify({'error': True, 'message': 'No Resource Found'}), 404)

    def post(self):
        data = request.json if isinstance(request.json, list) else [request.json]
        for d in data:
            try:
                db.session.begin_nested()
                if d['__action'] == 'add':
                    self.resource.add_relation(d)
                if d['__action'] == 'update':
                    self.resource.update_relation(d)
                elif d['__action'] == 'remove':
                    self.resource.remove_relation(d)
            except (ResourceNotFound, SQLIntegrityError, SQlOperationalError, CustomException) as e:
                db.session.rollback()
                e.message['error'] = True
                return make_response(jsonify(e.message), e.status)
        db.session.commit()

        return make_response(jsonify({'success': True, 'message': 'Updated Successfully', 'data': data}), 200)


class DataView(Resource):
    api_methods = [List, Fetch]
    decorators = [jwt_required]

    def __init__(self):
        if self.get_resource is not None:
            self.resource = self.get_resource()()
            self.add_method_decorator()

    @classmethod
    @abstractmethod
    def get_resource(cls) -> DataResourceType:
        pass

    def add_method_decorator(self):
        self.method_decorators = []
        # self.method_decorators.append(check_shop_access)
        self.method_decorators.append(roles_required(*[i for i in self.resource.roles_required]))
        self.method_decorators.append(roles_accepted(*[i for i in self.resource.roles_accepted]))

    @abstractmethod
    def get(self, slug=None):
        pass
