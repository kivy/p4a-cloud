__all__ = ('config', 'logger', )

from hotqueue import HotQueue
from ConfigParser import ConfigParser
from os.path import dirname, join
import logging

LOG_FILENAME = join(dirname(__file__), '..', 'logs', 'p4a.log')

# logger
logger = logging.getLogger('p4a')
logger.setLevel(logging.DEBUG)

handler = logging.FileHandler(LOG_FILENAME)
logger.addHandler(handler)


# configuration
config = ConfigParser()
config.add_section('www'),
config.set('www', 'secret_key', '')

config.add_section('database')
config.set('database', 'url', 'sqlite:////tmp/test.db')

# read existing file
config_fn = join(dirname(__file__), '..', 'config.cfg')
config.read(config_fn)

# write current config if possible
try:
    fd = open(config_fn, 'w')
    config.write(fd)
    fd.close()
except Exception:
    pass

# start the queue
qjob = HotQueue(
    'jobsubmit',
    host=config.get('hotqueue', 'host'),
    port=config.getint('hotqueue', 'port'),
    db=config.getint('hotqueue', 'db'),
    password=config.get('hotqueue', 'password'))

