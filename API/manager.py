import os
import urllib.parse as up

from werkzeug.middleware.proxy_fix import ProxyFix
from flask import url_for, make_response, jsonify
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

from src import api, db, ma, create_app, configs, bp, security, admin, celery, serializer_helper, sentry,\
    redis_store, sms, url_shortener, limiter, jwt, razor


config = os.environ.get('PYTH_SRVR', 'default')

config = configs.get(config)

extensions = [api, db, ma, security, admin, celery, serializer_helper, sentry, redis_store,
              sms, url_shortener, limiter, jwt, razor]
bps = [bp]

app = create_app(__name__, config, extensions=extensions, blueprints=bps)
app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=2)
manager = Manager(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)


@manager.shell
def _shell_context():
    return dict(
        app=app,
        db=db,
        ma=ma,
        config=config
        )


@manager.command
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)
        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        line = up.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, url))
        output.append(line)

    for line in sorted(output):
        print(line)


@manager.option('-A', '--application', dest='application', default='', required=True)
@manager.option('-n', '--name', dest='name')
@manager.option('-l', '--debug', dest='debug')
@manager.option('-f', '--logfile', dest='logfile')
@manager.option('-P', '--pool', dest='pool')
@manager.option('-Q', '--queue', dest='queue')
@manager.option('-c', '--concurrency', dest='concurrency', default=2)
def worker(application, concurrency, pool, debug, logfile, name, queue):
    celery.start()


@app.route('/api/v1/health', methods=['GET'])
def status():
    return make_response(jsonify({'success': True, "message": 'Success', 'count': 0}), 200)


@limiter.exempt
@app.route('/api/v1/ping', methods=['GET'])
def ping():
    # from time import sleep
    # import random
    # sleep(random.randint(2, 4))
    return make_response(jsonify({'success': True, "message": 'Success'}), 200)


if __name__ == "__main__":
    manager.run()
