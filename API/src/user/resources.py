from flask_security import current_user
from sqlalchemy import and_, or_

from src.user.models import UserToUser
from src.utils import ModelResource, operators as ops
from .schemas import User, UserSchema


class UserResource(ModelResource):

    model = User
    schema = UserSchema

    auth_required = True

    roles_accepted = ('admin', 'owner', 'staff')

    optional = ('stores', 'current_login_at', 'current_login_ip', 'created_on', 'fixed_dues', 'subscriptions',
                'last_login_at', 'last_login_ip', 'login_count', 'confirmed_at', 'permissions', 'retail_brand')

    exclude = ('password', 'roles', 'active')

    filters = {
        'username': [ops.Equal, ops.Contains],
        'name': [ops.Equal, ops.Contains],
        'active': [ops.Boolean],
        'id': [ops.Equal],
        'first_name': [ops.Equal, ops.StartsWith],

    }

    related_resource = {

    }

    order_by = ['email', 'id', 'name']

    only = ()

    def has_read_permission(self, qs):
        return qs.filter(User.id == current_user.id)

    def has_change_permission(self, obj):
        if current_user.has_role('admin') or current_user.has_role('owner'):
            if current_user.brand_id == obj.brand_id:
                return True
        elif current_user.has_role('staff'):
            if current_user.id == obj.id:
                return True
        return False

    def has_delete_permission(self, obj):
        if current_user.has_role('admin') or current_user.has_role('owner'):
            if current_user.brand_id == obj.brand_id:
                return True
        return False

    def has_add_permission(self, obj):
        if current_user.has_role('admin') or current_user.has_role('owner'):
            if current_user.brand_id == obj.brand_id:
                return True
        return False
