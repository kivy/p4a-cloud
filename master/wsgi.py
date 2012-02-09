import sys
sys.path.append('/home/dotcloud/current')
from web import app as application
from web.apps.frontend import frontend
application.register_blueprint(frontend)
application.debug = True

if __name__ == '__main__':
    application.run('0.0.0.0')

