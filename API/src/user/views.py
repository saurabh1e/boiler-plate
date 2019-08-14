from random import randint
from datetime import timedelta
from flask import request, jsonify, make_response, redirect, json
from flask_jwt_extended import (create_access_token, jwt_required)
from flask_restful import Resource
from flask_security.utils import verify_and_update_password, login_user
from flask_security import current_user
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from src import BaseView, limiter, db, redis_store, sms
from src import api
from src.user.schemas import UserSchema
from src.utils.api import set_user
from src.utils.methods import List, Fetch, Create, Update
from .models import User, UserToUser
from .resources import UserResource


@api.register()
class UserView(BaseView):
    api_methods = [List, Fetch, Create, Update]

    @classmethod
    def get_resource(cls):
        return UserResource


class UserLoginResource(Resource):
    model = User

    decorators = [limiter.limit("300/day;30/hour;5/minute;2/second")]

    def post(self):

        if request.json:
            data = request.json
            print(data)
            user = self.model.query.filter(self.model.email == data['email']).first()
            print(user)
            if user and verify_and_update_password(data['password'], user) and login_user(user):
                expires = timedelta(days=365)
                user = UserSchema(only=('id', 'email', 'first_name', 'last_name', 'roles', 'business_name')).dump(user).data
                return make_response(
                    jsonify({'id': user['id'],
                             'authentication_token': create_access_token(identity=user, expires_delta=expires)}), 200)
            else:
                return make_response(jsonify({'meta': {'code': 403}}), 403)

        else:
            data = request.form
            user = self.model.query.filter(self.model.email == data['email']).first()
            if user and verify_and_update_password(data['password'], user) and login_user(user):
                return make_response(redirect('/admin/', 302))
            else:
                return make_response(redirect('/api/v1/login', 403))


class UserRegisterResource(Resource):
    model = User
    schema = UserSchema

    def post(self):
        data = request.json
        user = User.query.filter(User.mobile_number == data['mobile_number']).first()
        if user:
            return make_response(jsonify({}), 400)
        user, errors = self.schema().load(data)
        if errors:
            return make_response(jsonify(errors), 400)
        # try:
        #     db.session.add(user)
        #     db.session.commit()
        # except (IntegrityError, InvalidRequestError) as e:
        #     print(e)
        #     db.session.rollback()
        #     return make_response(jsonify(str(e)), 400)
        redis_store.setex('user:' + data['mobile_number'], 10 * 600, json.dumps(data))
        send_otp(user.mobile_number, 'Your otp to sign up at zoPay is {0}. Valid for 10 minutes.')
        return make_response(jsonify({}), 200)


def send_otp(phone: str, content) -> bool:
    otp = randint(100000, 999999)
    redis_store.setex(phone, 10 * 600, otp)
    try:
        business_name = current_user.business_name
    except AttributeError:
        business_name = ''
    content = [dict(message=content.format(otp, business_name), to=[phone])]
    sms.send_sms(content=content)
    return True


class UserVerifyResource(Resource):
    model = User
    schema = UserSchema

    def post(self):
        data = request.json
        if redis_store.get('user:' + data['mobile_number']) and redis_store.get(data['mobile_number']).decode('utf-8') == str(data['otp']):
            user, errors = self.schema().load(json.loads(redis_store.get('user:' + data['mobile_number']).decode('utf-8')))
            if errors:
                return make_response(jsonify(errors), 400)
            try:
                db.session.add(user)
                db.session.commit()
            except (IntegrityError, InvalidRequestError) as e:
                print(e)
                db.session.rollback()
                return make_response(jsonify({}), 400)
            expires = timedelta(days=365)
            return make_response(
                jsonify({'id': user.id,
                         'user': UserSchema().dump(user, only=('id', 'email', 'first_name', 'last_name', 'roles', 'business_name')),
                         'authentication_token': create_access_token(identity=user.id,
                                                                                    expires_delta=expires)}), 200)
        else:
            return make_response(jsonify({'meta': {'code': 403}}), 403)


class CustomerRegistrationResource(Resource):
    model = User
    method_decorators = [set_user, jwt_required]

    def post(self):
        data = request.json
        user = self.model.query.filter(self.model.mobile_number == data['mobile_number']).first()
        if not user:
            user_data = dict(mobile_number=data['mobile_number'], first_name=data['first_name'])
            user, errors = UserSchema().load(user_data)
            if errors:
                return make_response(jsonify(errors), 400)
            db.session.add(user)
            db.session.commit()
        send_otp(data['mobile_number'],
                 'Your otp to verify your number at {1} is {0}. Please share your otp with {1}')
        return make_response(jsonify({}), 200)


class CustomerVerifyResource(Resource):
    model = User
    method_decorators = [set_user, jwt_required]

    def post(self):
        data = request.json
        user = self.model.query.filter(self.model.mobile_number == data['mobile_number']).first()
        if user and redis_store.get(data['mobile_number']).decode('utf-8') == data['otp']:

            utu = UserToUser()
            utu.business_owner_id = current_user.id
            utu.customer_id = user.id
            db.session.add(utu)
            db.session.commit()
            return make_response(jsonify({'id': user.id, 'first_name': user.first_name}), 200)
        else:
            return make_response(jsonify({'meta': {'code': 403}}), 403)


api.add_resource(UserLoginResource, '/login/', endpoint='login')
api.add_resource(UserRegisterResource, '/register/', endpoint='register')
api.add_resource(UserVerifyResource, '/verify/', endpoint='verify')

api.add_resource(CustomerRegistrationResource, '/customer_register/', endpoint='customer_register')
api.add_resource(CustomerVerifyResource, '/customer_verify/', endpoint='customer_verify')