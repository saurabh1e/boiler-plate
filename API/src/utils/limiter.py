from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


@limiter.request_filter
def header_whitelist():
    token = request.headers.get('authorization')
    return request.method == 'OPTIONS'
