import sys
import os
from os.path import dirname, join
sys.path.insert(0, dirname(__file__))
activate_this = join(dirname(__file__), '.env', 'bin', 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

from web import app as application
from web.apps.frontend import frontend
application.register_blueprint(frontend)
application.debug = True

if __name__ == '__main__':
    application.run('0.0.0.0')

