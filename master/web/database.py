__all__ = ('engine', 'db_session', 'init_db')

from web.config import config
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

url = config.get('database', 'url')
keys = {'convert_unicode': True}
if url.startswith('mysql'):
    keys['pool_recycle'] = 3600
engine = create_engine(url, **keys)
db_session = scoped_session(sessionmaker(
    autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    Base.metadata.create_all(bind=engine)

