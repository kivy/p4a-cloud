__all__ = ('app', )

from flask import Flask
from web.config import config
from time import time, localtime, strftime

def delta_time(seconds):
    seconds = int(seconds)
    minutes = seconds // 60
    hours = minutes // 60
    minutes = minutes % 60
    days = hours // 24
    hours = hours % 24
    seconds = seconds % 60
    k = {'seconds': seconds, 'minutes': minutes,
         'hours': hours, 'days': days}
    if days:
        return '%(days)sj %(hours)dh %(minutes)dm %(seconds)ds' % k
    elif hours:
        return '%(hours)dh %(minutes)dm %(seconds)ds' % k
    elif minutes:
        return '%(minutes)dm %(seconds)ds' % k
    else:
        return '%(seconds)ds' % k


app = Flask(__name__)
app.secret_key = config.get('www', 'secret_key')
app.jinja_env.globals['time'] = time
app.jinja_env.filters['delta_time'] = delta_time

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y %H:%M'):
    try:
        r=strftime(format, localtime(float(value)))
        #"%Y-%m-%d %H:%M:%S"
    except:
        r=''
    return r

