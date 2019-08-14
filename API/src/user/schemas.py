from src import ma, BaseSchema
from .models import User, Role, UserRole


class UserSchema(BaseSchema):
    class Meta:
        model = User
        exclude = ('updated_on', 'my_payments', 'my_dues')

    id = ma.Integer(dump_only=True)
    email = ma.Email(required=False)
    # username = ma.String(required=True)
    first_name = ma.String(load=True)
    roles = ma.Nested('RoleSchema', many=True, dump_only=True, only=('id', 'name'))
    fixed_dues = ma.Integer(dump_only=True)
    subscriptions = ma.Integer(dump_only=True)


class RoleSchema(BaseSchema):
    class Meta:
        model = Role
        exclude = ('updated_on', 'created_on', 'users')

    id = ma.UUID()
    name = ma.String()
    permissions = ma.Nested('PermissionSchema', many=True, dump_only=True, only=('id', 'name'))


class UserRoleSchema(BaseSchema):
    class Meta:
        model = UserRole
        exclude = ('created_on', 'updated_on')

    id = ma.UUID(load=True)
    user_id = ma.UUID(load=True)
    role_id = ma.UUID(load=True)
    user = ma.Nested('UserSchema', many=False)
    role = ma.Nested('RoleSchema', many=False)
