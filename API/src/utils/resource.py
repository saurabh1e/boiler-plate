from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import request
from flask_security import current_user
from sqlalchemy import and_
from sqlalchemy.exc import OperationalError, IntegrityError, InvalidRequestError
from sqlalchemy.orm.exc import DetachedInstanceError
from typing import List, Tuple, Dict

from .exceptions import ResourceNotFound, SQLIntegrityError, SQlOperationalError, CustomException, RequestNotAllowed, \
    SQlInvalidRequestError, SQLDetachedInstanceError
from .models import db
from .sentry import sentry


class ModelResource(ABC):
    model = None
    schema = None

    filters = {}

    external_filter: Dict = {}

    max_limit: int = 100

    default_limit: int = 50

    exclude_related_resource: Tuple[str] = ()

    order_by: List[str] = []

    only: Tuple[str] = ()

    exclude: Tuple[str] = ('external_id',)

    include: Tuple[str] = ()

    optional: Tuple[str] = ()

    page: int = 1

    auth_required: bool = False

    export: bool = False

    max_export_limit: int = 5000

    roles_accepted: Tuple[str] = ()

    roles_required: Tuple[str] = ()

    def __init__(self):

        if request.args.getlist('__only'):
            if len(request.args.getlist('__only')) == 1:
                self.obj_only = tuple(request.args.getlist('__only')[0].split(','))
            else:
                self.obj_only = tuple(request.args.getlist('__only'))
        else:
            self.obj_only = self.only

        self.obj_exclude = []
        if request.args.getlist('__exclude'):
            if len(request.args.getlist('__exclude')) == 1:
                self.obj_exclude = request.args.getlist('__exclude')[0].split(',')
            else:
                self.obj_exclude = request.args.getlist('__exclude')

        self.obj_exclude.extend(list(self.exclude))
        self.obj_optional = list(self.optional)

        if request.args.getlist('__include'):
            if len(request.args.getlist('__include')) == 1:
                optionals = request.args.getlist('__include')[0].split(',')
            else:
                optionals = request.args.getlist('__include')

            for optional in optionals:
                try:
                    self.obj_optional.remove(optional)
                except ValueError:
                    pass

        self.obj_exclude.extend(self.obj_optional)

        self.page = int(request.args.get('__page')) if request.args.get('__page') else 1
        self.limit = int(request.args.get('__limit')) if request.args.get('__limit') \
                                                         and int(
            request.args.get('__limit')) <= self.max_limit else self.default_limit

    def apply_filters(self, queryset, **kwargs):
        for k, v in kwargs.items():
            array_key = k.split('__')
            if array_key[0] == '' and array_key[1] in self.filters.keys():
                for operator in self.filters.get(array_key[1]):
                    if operator.op == array_key[2]:
                        queryset = operator().prepare_queryset(queryset, self.model, array_key[1], v)

            elif array_key[0] == '' and array_key[1] in self.external_filter.keys():
                query_filter = self.external_filter.get(array_key[1])
                for operator in query_filter['filters']:
                    if operator.op == array_key[2]:
                        joined_tables = [mapper.class_ for mapper in queryset._join_entities]
                        if not query_filter['model'] in joined_tables:
                            queryset = queryset.join(query_filter['model'],
                                                     and_(getattr(query_filter['model'],
                                                                  query_filter['join']) == self.model.id))

                        queryset = operator().prepare_queryset(queryset, query_filter['model'], array_key[1], v)

        if '__distinct_by' in request.args:
            queryset = queryset.distinct(getattr(self.model, request.args['__distinct_by']))
        return queryset

    def apply_ordering(self, queryset, order_by_list):
        if len(order_by_list) == 1:
            order_by_list = order_by_list[0].split(',')
        for order_by in order_by_list:
            desc = False
            if order_by.startswith('-'):
                desc = True
                order_by = order_by.replace('-', '')
            if order_by in self.order_by:
                if desc:
                    queryset = queryset.order_by(getattr(self.model, order_by).desc())
                else:
                    queryset = queryset.order_by(getattr(self.model, order_by))
        return queryset

    def patch_resource(self, slug):
        obj = self.model.query.get(slug)
        if obj and self.has_change_permission(obj):
            obj, errors = self.schema().load(request.json, instance=obj, partial=True)
            if errors:
                db.session.rollback()
                return {'error': True, 'message': str(errors)}, 400

            try:
                if self.has_change_permission(obj):
                    db.session.commit()
                    self.after_objects_save([obj])
                else:
                    db.session.rollback()
                    return {'error': True, 'message': 'Forbidden Permission Denied To Change Resource'}, 403
            except IntegrityError:
                sentry.captureException()
                db.session.rollback()
                raise SQLIntegrityError(data={}, message='Integrity Error', operation='Adding Resource',
                                        status=400)
            except OperationalError:
                sentry.captureException()
                db.session.rollback()
                raise SQlOperationalError(data={}, message='Operational Error', operation='Adding Resource',
                                          status=400)
            except InvalidRequestError:
                sentry.captureException()
                db.session.rollback()
                raise SQlInvalidRequestError(data={}, message='Invalid Request Error', operation='Adding Resource',
                                             status=400)
            except DetachedInstanceError:
                sentry.captureException()
                db.session.rollback()
                raise SQLDetachedInstanceError(data={}, message='Invalid Request Error', operation='Adding Resource',
                                               status=500)

            return {'success': True, 'message': 'obj updated successfully',
                    'data': self.schema(exclude=tuple(self.obj_exclude), only=tuple(self.obj_only))
                        .dump(obj).data}, 200

        return {'error': True, 'message': 'Forbidden Permission Denied To Change Resource'}, 403

    def update_resource(self):
        data = request.json if isinstance(request.json, list) else [request.json]
        objects = []
        for d in data:
            obj = self.schema().get_instance(d)
            if not obj or not self.has_change_permission(obj):
                return {'error': True, 'message': 'Forbidden Permission Denied To Add Resource'}, 403
            obj, errors = self.schema().load(d, instance=obj)
            if errors:
                sentry.captureMessage(errors)
                db.session.rollback()
                return {'error': True, 'message': str(errors)}, 400

            if not self.has_change_permission(obj):
                db.session.rollback()
                return {'error': True, 'message': 'Forbidden Permission Denied To Add Resource'}, 403
            try:
                db.session.commit()
                objects.append(obj)
            except IntegrityError:
                sentry.captureException()
                db.session.rollback()
                raise SQLIntegrityError(data=d, message='Integrity Error', operation='Updating Resource', status=400)
            except OperationalError:
                sentry.captureException()
                db.session.rollback()
                raise SQlOperationalError(data=d, message='Operational Error', operation='Updating Resource',
                                          status=400)
            except InvalidRequestError:
                sentry.captureException()
                db.session.rollback()
                raise SQlInvalidRequestError(data=d, message='Invalid Request Error', operation='Adding Resource',
                                             status=400)
        self.after_objects_save(objects)
        return {'success': True, 'message': 'Resource Updated successfully',
                'data': self.schema(exclude=tuple(self.obj_exclude), only=tuple(self.obj_only))
                    .dump(objects, many=True).data}, 201

    def save_resource(self):
        data = request.json if isinstance(request.json, list) else [request.json]
        objects, errors = self.schema().load(data, session=db.session, many=True)
        if errors:
            sentry.captureMessage(errors)
            db.session.rollback()
            return {'error': True, 'message': str(errors)}, 400

        if self.has_add_permission(objects):
            db.session.add_all(objects)
        else:
            db.session.rollback()
            return {'error': True, 'message': 'Forbidden Permission Denied To Add Resource'}, 403
        try:
            db.session.commit()
            self.after_objects_save(objects)
        except IntegrityError:
            sentry.captureException()
            db.session.rollback()
            raise SQLIntegrityError(data=data, message='Integrity Error', operation='Adding Resource', status=400)
        except OperationalError:
            sentry.captureException()
            db.session.rollback()
            raise SQlOperationalError(data=data, message='Operational Error', operation='Adding Resource', status=400)
        except InvalidRequestError:
            sentry.captureException()
            db.session.rollback()
            raise SQlInvalidRequestError(data=data, message='Invalid Request Error', operation='Adding Resource',
                                         status=400)
        return {'success': True, 'message': 'Resource added successfully',
                'data': self.schema(exclude=tuple(self.obj_exclude), only=tuple(self.obj_only))
                    .dump(objects, many=True).data}, 201

    @abstractmethod
    def has_read_permission(self, qs):
        return qs

    @abstractmethod
    def has_change_permission(self, obj) -> bool:
        return True

    @abstractmethod
    def has_delete_permission(self, obj) -> bool:
        return True

    @abstractmethod
    def has_add_permission(self, obj) -> bool:
        return True

    def after_objects_save(self, objects) -> None:
        pass


class AssociationModelResource(ABC):
    model = None

    schema = None

    filters = {}

    max_limit: int = 100

    default_limit: int = 50

    exclude_related_resource: Tuple[str] = ()

    order_by: List[str] = []

    only: Tuple[str] = ()

    exclude: Tuple[str] = ()

    include: Tuple[str] = ()

    optional: Tuple[str] = ()

    page: int = 1

    auth_required = False

    roles_accepted: Tuple[str] = ()

    roles_required: Tuple[str] = ()

    def __init__(self):

        if request.args.getlist('__only'):
            if len(request.args.getlist('__only')) == 1:
                self.obj_only = tuple(request.args.getlist('__only')[0].split(','))
            else:
                self.obj_only = tuple(request.args.getlist('__only'))
        else:
            self.obj_only = self.only

        self.obj_exclude = []
        if request.args.getlist('__exclude'):
            if len(request.args.getlist('__exclude')) == 1:
                self.obj_exclude = request.args.getlist('__exclude')[0].split(',')
            else:
                self.obj_exclude = request.args.getlist('__exclude')

        self.obj_exclude.extend(list(self.exclude))
        self.obj_optional = list(self.optional)

        if request.args.getlist('__include'):
            if len(request.args.getlist('__include')) == 1:
                optionals = request.args.getlist('__include')[0].split(',')
            else:
                optionals = request.args.getlist('__include')

            for optional in optionals:
                try:
                    self.obj_optional.remove(optional)
                except ValueError:
                    sentry.captureException()
                    pass

        self.obj_exclude.extend(self.obj_optional)

        self.page = int(request.args.get('__page')) if request.args.get('__page') else 1
        self.limit = int(request.args.get('__limit')) if request.args.get('__limit') \
                                                         and int(
            request.args.get('__limit')) <= self.max_limit else self.default_limit

    def apply_filters(self, queryset, **kwargs):
        for k, v in kwargs.items():
            array_key = k.split('__')
            if array_key[0] == '' and array_key[1] in self.filters.keys():
                for operator in self.filters.get(array_key[1]):
                    if operator.op == array_key[2]:
                        queryset = operator().prepare_queryset(queryset, self.model, array_key[1], v)

        return queryset

    def apply_ordering(self, queryset, order_by):
        desc = False
        if order_by.startswith('-'):
            desc = True
            order_by = order_by.replace('-', '')
        if order_by in self.order_by:
            if desc:
                queryset = queryset.order_by(getattr(self.model, order_by).desc())
            else:
                queryset = queryset.order_by(getattr(self.model, order_by))

        return queryset

    def add_relation(self, data):
        obj, errors = self.schema().load(data, session=db.session)
        if errors:
            sentry.captureMessage(errors)
            raise CustomException(data=data, message=str(errors), operation='adding relation')

        if self.has_add_permission(obj, data):
            db.session.add(obj)
            try:
                db.session.commit()
                self.after_objects_save(obj)
            except IntegrityError as e:
                sentry.captureException()
                raise SQLIntegrityError(data=data, message=str(e), operation='adding relation', status=400)
            except OperationalError as e:
                sentry.captureException()
                raise SQLIntegrityError(data=data, message=str(e), operation='adding relation', status=400)
        else:
            sentry.captureMessage(data)
            raise RequestNotAllowed(data=data, message='Object not Found', operation='adding relation',
                                    status=401)

    def update_relation(self, data):
        obj = self.model.query.get(data['id'])
        if obj and self.has_change_permission(obj, data):
            obj, errors = self.schema().load(data, instance=obj)
            if errors:
                sentry.captureMessage(errors)
                raise CustomException(data=data, message=str(errors), operation='updating relation')
            if self.has_change_permission(obj, data):
                raise CustomException(data=data, message='Permission Denied', operation='adding relation')
            try:
                db.session.commit()
                self.after_objects_save(obj)
            except IntegrityError:
                sentry.captureException()
                db.session.rollback()
                raise SQLIntegrityError(data=data, message='Integrity Error', operation='Adding Resource', status=400)
            except OperationalError:
                sentry.captureException()
                db.session.rollback()
                raise SQlOperationalError(data=data, message='Operational Error', operation='Adding Resource',
                                          status=400)
            else:
                sentry.captureMessage(data)
                raise RequestNotAllowed(data=data, message='Object not Found', operation='deleting relation',
                                        status=401)
        else:
            raise ResourceNotFound(data=data, message='Object not Found', operation='Updating relation', status=404)

    def remove_relation(self, data):
        obj = self.model.query
        for k, v in data.items():
            if hasattr(self.model, k):
                obj = obj.filter(getattr(self.model, k) == v)
        obj = obj.first()
        if obj:
            if self.has_delete_permission(obj, data):
                db.session.delete(obj)
                try:
                    db.session.commit()
                except IntegrityError:
                    sentry.captureException()
                    raise SQLIntegrityError(data=data, message='Integrity Error', operation='deleting relation',
                                            status=400)
                except OperationalError:
                    sentry.captureException()
                    raise SQLIntegrityError(data=data, message='Operational Error', operation='deleting relation',
                                            status=400)
            else:
                raise RequestNotAllowed(data=data, message='Object not Found', operation='deleting relation',
                                        status=401)
        else:
            raise ResourceNotFound(data=data, message='Object not Found', operation='deleting relation', status=404)

    @abstractmethod
    def has_read_permission(self, qs):
        return qs

    @abstractmethod
    def has_change_permission(self, obj, data) -> bool:
        return True

    @abstractmethod
    def has_delete_permission(self, obj, data) -> bool:
        return True

    @abstractmethod
    def has_add_permission(self, obj, data) -> bool:
        return True

    def after_objects_save(self, obj) -> None:
        pass


class DataResource(ABC):
    model = None

    filters = {}

    external_filter: Dict = {}

    max_limit: int = 100

    default_limit: int = 50

    order_by: List[str] = []

    page: int = 1

    auth_required: bool = True

    export: bool = True

    max_export_limit: int = 5000

    roles_required: Tuple[str] = ()

    block_report: bool = True

    retail_shop_ids: List[str] = []

    end_date = datetime.now()

    start_date = datetime.now() - relativedelta(days=30)

    roles_accepted: Tuple[str] = ('admin', 'owner')

    headers: List[Tuple[str]] = ()

    group_by: Tuple[str] = ()

    def __init__(self):
        try:
            if len(request.args.getlist('__retail_shop_id__in')):
                outlets = request.args.getlist('__retail_shop_id__in')
                if len(outlets) == 1:
                    outlets = outlets[0].split(',')
                self.retail_shop_ids = outlets
            else:
                self.retail_shop_ids = current_user.retail_shop_ids

            if '__start_date__equal' in request.args:
                self.start_date = datetime.strptime(request.args.get('__start_date__equal'), '%Y-%m-%dT%H:%M:%S.%fZ')
            if '__end_date__equal' in request.args:
                self.end_date = datetime.strptime(request.args.get('__end_date__equal'), '%Y-%m-%dT%H:%M:%S.%fZ')

            if self.start_date == self.end_date:
                self.end_date = self.end_date + relativedelta(days=1)
            elif self.start_date > self.end_date:
                self.start_date, self.end_date = self.end_date, self.start_date

            if len(self.retail_shop_ids) > 1 and (self.end_date - self.start_date) > timedelta(days=31):
                self.start_date = self.end_date - relativedelta(days=1)

            elif (self.end_date - self.start_date) > timedelta(days=31):
                self.start_date = self.end_date - relativedelta(days=1)

            if self.retail_shop_ids.__len__() == 1:
                if current_user.has_permission('block_open_reports') and self.block_report:
                    last_closing = current_user.last_closing_time(self.retail_shop_ids[0])
                    print(last_closing, self.start_date, self.end_date)
                    if last_closing < self.start_date or last_closing < self.end_date:
                        self.start_date = self.end_date = last_closing
        except KeyError:
            pass

        self.page = int(request.args.get('__page')) if request.args.get('__page') else 1
        self.limit = int(request.args.get('__limit')) if request.args.get('__limit') \
                                                         and int(
            request.args.get('__limit')) <= self.max_limit else self.default_limit

    def apply_filters(self, queryset, **kwargs):
        for k, v in kwargs.items():
            array_key = k.split('__')
            if array_key[0] == '' and array_key[1] in self.filters.keys():
                for operator in self.filters.get(array_key[1]):
                    if operator.op == array_key[2]:
                        queryset = operator().prepare_queryset(queryset, self.model, array_key[1], v)

            elif array_key[0] == '' and array_key[1] in self.external_filter.keys():
                query_filter = self.external_filter.get(array_key[1])
                for operator in query_filter['filters']:
                    if operator.op == array_key[2]:
                        queryset = queryset.join(query_filter['model'],
                                                 and_(getattr(query_filter['model'],
                                                              query_filter['join']) == self.model.id))

                        queryset = operator().prepare_queryset(queryset, query_filter['model'], array_key[1], v)

        if '__distinct_by' in request.args:
            queryset = queryset.distinct(getattr(self.model, request.args['__distinct_by']))
        return queryset

    def apply_ordering(self, queryset, order_by_list):
        if len(order_by_list) == 1:
            order_by_list = order_by_list[0].split(',')
        for order_by in order_by_list:
            desc = False
            if order_by.startswith('-'):
                desc = True
                order_by = order_by.replace('-', '')
            if order_by in self.order_by:
                if desc:
                    queryset = queryset.order_by(getattr(self.model, order_by).desc())
                else:
                    queryset = queryset.order_by(getattr(self.model, order_by))
        return queryset

    @abstractmethod
    def construct_query_set(self):
        return

    def get_export_headers(self):

        return self.headers
