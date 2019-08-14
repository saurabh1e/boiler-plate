from flask_security import Security
from flask_security.datastore import SQLAlchemyUserDatastore

from src.user import models

user_data_store = SQLAlchemyUserDatastore(models.db, models.User, models.Role)


class FlaskSecurity(Security):
    def __init__(self, app=None):
        if app:
            super(FlaskSecurity, self).__init__(app, user_data_store)

    def init_app(self, app, datastore=None, register_blueprint=True,
                 login_form=None, confirm_register_form=None,
                 register_form=None, forgot_password_form=None,
                 reset_password_form=None, change_password_form=None,
                 send_confirmation_form=None, passwordless_login_form=None,
                 anonymous_user=None):
        super().init_app(app, user_data_store)


security = FlaskSecurity()
