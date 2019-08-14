from flask_admin.contrib.sqla import ModelView

from flask_security import current_user

from src import admin, db

from src.user.models import User, Role, UserRole, UserToUser
from src.dues.models import Due, Payment


class MyModel(ModelView):
    page_size = 100
    can_set_page_size = True
    can_view_details = True

    def is_accessible(self):
        return current_user.has_role('admin')


admin.add_view(MyModel(User, session=db.session))
admin.add_view(MyModel(Role, session=db.session))
admin.add_view(MyModel(UserRole, session=db.session))

admin.add_view(MyModel(Due, session=db.session))
admin.add_view(MyModel(Payment, session=db.session))
admin.add_view(MyModel(UserToUser, session=db.session))
