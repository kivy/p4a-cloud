__all__ = ('config', 'logger', )

from hotqueue import HotQueue
from ConfigParser import ConfigParser
from os.path import dirname, join, exists
from redis import Redis
import json

# configuration
config = ConfigParser()
config.add_section('www'),
config.set('www', 'secret_key', 'http://build.kivy.org/')
config.set('www', 'secret_key', '')

config.add_section('database')
config.set('database', 'url', 'sqlite:////tmp/test.db')

config.add_section('redis')
config.set('redis', 'host', 'localhost')
config.set('redis', 'port', '6379')
config.set('redis', 'password', '')

# are we on dotcloud ?
env = None
try:
    with open('/home/dotcloud/environment.json') as fd:
        env = json.load(fd)
except:
    pass

if env is None:
    # read existing file
    config_fn = join(dirname(__file__), '..', 'config.cfg')
    if exists(config_fn):
        config.read(config_fn)

    # write current config if possible
    try:
        fd = open(config_fn, 'w')
        config.write(fd)
        fd.close()
    except Exception:
        pass
else:
    # use dotcloud env
    config.set('database', 'url', env['DOTCLOUD_DATA_MYSQL_URL'] + '/mysql')
    config.set('redis', 'host', env['DOTCLOUD_QUEUE_REDIS_HOST'])
    config.set('redis', 'port', env['DOTCLOUD_QUEUE_REDIS_PORT'])
    config.set('redis', 'password', env['DOTCLOUD_QUEUE_REDIS_PASSWORD'])

# start the queue
qjob = HotQueue(
    'jobsubmit',
    host=config.get('redis', 'host'),
    port=config.getint('redis', 'port'),
    password=config.get('redis', 'password'),
    db=0)

# Redis database connector
r = Redis(
    host=config.get('redis', 'host'),
    port=config.getint('redis', 'port'),
    password=config.get('redis', 'password'),
    db=1)

