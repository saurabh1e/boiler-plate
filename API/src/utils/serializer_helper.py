from itsdangerous import URLSafeTimedSerializer


class SerializerHelper(object):
    key = None
    salt = None

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app=None):
        self.key = app.config.get('SECRET_KEY', None)
        self.salt = app.config.get('SECURITY_LOGIN_SALT', None)

    def get_serializer(self):
        return URLSafeTimedSerializer(self.key, self.salt)

    def serialize_data(self, data):
        return self.get_serializer().dumps(data)

    def deserialize_data(self, data, time=None):
        return self.get_serializer().loads(data, time)


serializer_helper = SerializerHelper()
