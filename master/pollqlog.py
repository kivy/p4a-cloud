#!/usr/bin/env python
'''
Poll the log queue (builder -> webservice).
Must be started on the same server than the web service.
'''

import sys
import os
sys.path = [os.path.join(os.path.dirname(__file__))] + sys.path

from web.config import config, r
from hotqueue import HotQueue
from web.job import read_job

# start a thread for listing qlog
qlog = HotQueue(
    'joblog',
    host=config.get('redis', 'host'),
    port=config.getint('redis', 'port'),
    password=config.get('redis', 'password'),
    db=0)

cache = {}

for log in qlog.consume():
    print log
    if 'cmd' not in log or 'uid' not in log:
        continue
    cmd = log['cmd']
    uid = log['uid']

    jobkey = 'job:%s' % uid
    if not r.keys(jobkey):
        continue

    if cmd == 'status':
        r.set(jobkey + ':build_status', log['msg'])
    elif cmd == 'exception':
        r.set(jobkey + ':build_status', '[1/1] Error')
        r.set(jobkey + ':is_failed', 1)
        r.set(jobkey + ':fail_message', log['msg'])

    if cmd == 'log' or cmd == 'exception':
        logkey = 'log:%s' % uid
        if not r.keys(logkey):
            r.set(logkey, 1)
            lidx = 1
        else:
            lidx = r.incr(logkey)
        logkeytxt = logkey + ':%d' % lidx
        if cmd == 'log':
            r.set(logkeytxt, log['line'])
        else:
            r.set(logkeytxt, log['msg'])

    if cmd == 'exception':
        job = read_job(uid)
        if job:
            job.notify()

