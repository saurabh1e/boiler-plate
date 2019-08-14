import os

basedir = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = False
    SQLALCHEMY_EXPIRE_ON_COMMIT = False

    MARSHMALLOW_STRICT = True
    MARSHMALLOW_DATEFORMAT = 'rfc'

    SECRET_KEY = 'test'
    SECURITY_LOGIN_SALT = 'test'
    SECURITY_PASSWORD_HASH = 'pbkdf2_sha512'
    SECURITY_TRACKABLE = True
    SECURITY_PASSWORD_SALT = 'test'
    WTF_CSRF_ENABLED = False
    SECURITY_LOGIN_URL = '/api/v1/login/'
    SECURITY_LOGOUT_URL = '/api/v1/logout/'
    SECURITY_REGISTER_URL = '/api/v1/register/'
    SECURITY_RESET_URL = '/api/v1/reset/'
    SECURITY_CONFIRM_URL = '/api/v1/confirm/'
    SECURITY_REGISTERABLE = False
    SECURITY_CONFIRMABLE = True
    SECURITY_RECOVERABLE = False
    SECURITY_POST_LOGIN_VIEW = '/admin/'
    SECURITY_TOKEN_AUTHENTICATION_HEADER = 'Authorization'
    MAX_AGE = 86400

    DOMAIN = 'http://127.0.0.1:5000/api/v1/'

    RATELIMIT_DEFAULT = "24000/day;2400/hour;100/minute;6/second"
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_STRATEGY = 'fixed-window'
    CELERY_TASK_ACKS_LATE = True
    JWT_SECRET_KEY = 'test'
    JWT_HEADER_NAME = 'authorization'

    MSG91_KEY = os.environ.get('MSG91_KEY')
    MSG91_URL = 'http://api.msg91.com/api/v2/sendsms'

    BROKER_URL = os.environ.get('REDIS_URL') #'amqp://guest:@127.0.0.1:5672/'
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL')
    CELERY_BROKER_URL = os.environ.get('REDIS_URL')

    @staticmethod
    def init_app(app):
        pass

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SENTRY_USER_ATTRS = ['name', 'email']


class DevConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    REDIS_URL = os.environ.get('REDIS_URL')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URI')
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL')
    RAZOR_PAY_KEY = os.environ.get('DEV_RAZOR_PAY_KEY')
    RAZOR_PAY_SECRET = os.environ.get('DEV_RAZOR_PAY_SECRET')

    #BROKER_URL = "redis://:@localhost:6379/0" #'amqp://guest:@127.0.0.1:5672/'
    #CELERY_RESULT_BACKEND = "redis://:@localhost:6379/0"
    #CELERY_BROKER_URL = "redis://:@localhost:6379/0"


class TestConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    REDIS_URL = os.environ.get('REDIS_URL')
    BROKER_URL = os.environ.get('PROD_BROKER_URL')
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')


class ProdConfig(BaseConfig):
    REDIS_URL = os.environ.get('PROD_REDIS_URL')
    RATELIMIT_STORAGE_URL = os.environ.get('PROD_REDIS_URL')
    BROKER_URL = os.environ.get('PROD_BROKER_URL')
    RESULT_BACKEND = os.environ.get('PROD_RESULT_BACKEND')
    SQLALCHEMY_DATABASE_URI = os.environ.get('PROD_DATABASE_URI')

    MSG91_KEY = os.environ.get('MSG91_KEY')
    SENTRY_CONFIG = {
        'dsn': os.environ.get('SENTRY_CONFIG')
    }

    JWT_SECRET_KEY = os.environ.get('PROD_JWT_SECRET_KEY')
    SECRET_KEY = os.environ.get('PROD_SECRET_KEY')
    SECURITY_LOGIN_SALT = os.environ.get('PROD_SECURITY_LOGIN_SALT')
    SECURITY_PASSWORD_SALT = os.environ.get('PROD_SECURITY_PASSWORD_SALT')
    DOMAIN = os.environ.get('PROD_DOMAIN')
    RAZOR_PAY_KEY = os.environ.get('PROD_RAZOR_PAY_KEY')
    RAZOR_PAY_SECRET = os.environ.get('PROD_RAZOR_PAY_SECRET')


configs = {
    'dev': DevConfig,
    'testing': TestConfig,
    'prod': ProdConfig,
    'default': DevConfig
}
