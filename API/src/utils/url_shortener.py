import requests
from requests.exceptions import ConnectionError, Timeout


class GoogleUrlShortener(object):

    key = None
    url = None
    headers = {'content-type': 'application/json'}
    domain = None

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app=None):
        self.key = app.config.get('GOOGLE_URL_SHORTENER_KEY')
        self.url = app.config.get('GOOGLE_URL_SHORTENER_URL')
        self.domain = app.config.get('DOMAIN')

    def get_url(self, link):
        return self.domain + link

    def get_short_url(self, link):
        try:
            r = requests.post(self.url, params=dict(key=self.key), json=dict(longUrl=self.domain+link),
                              headers=self.headers, timeout=5)
        except (ConnectionError, Timeout) as e:
            print(e)
            raise e
        if 200 <= r.status_code < 300:
            return r.json()['id']
        return None

    def get_url_analytics(self, link):
        r = requests.get(self.url, params=dict(key=self.key, shortUrl=link, projection='FULL'))
        if 200 <= r.status_code < 300:
            return r.json()
        return None

url_shortener = GoogleUrlShortener()

