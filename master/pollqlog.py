#!/usr/bin/env python
'''
Poll the log queue (builder -> webservice).
Must be started on the same server than the web service.
'''

import sys
import os
import subprocess
sys.path = [os.path.join(os.path.dirname(__file__))] + sys.path

from web.config import config, r
from hotqueue import HotQueue
from web.job import read_job, JobObj
from time import time, sleep

# start a thread for listing qlog
qlog = HotQueue(
    'joblog',
    host=config.get('redis', 'host'),
    port=config.getint('redis', 'port'),
    password=config.get('redis', 'password'),
    db=0)

qlog.put({'cmd': 'purge', 'uid': 'moij'})

def loop_handle(log):
    print log
    if 'cmd' not in log or 'uid' not in log:
        return
    cmd = log['cmd']
    uid = log['uid']

    if cmd == 'purge':
        # search all projects done last 48h
        keys = r.keys('job:*:dt_added')
        print keys
        to_delete = []
        ctime = time()
        for key in keys:
            dt = ctime - float(r.get(key))
            print 'checked', key[4:-9], dt
            if dt > 60 * 60 * 48:
                print 'going to delete', key[4:-9], ', delta is', dt
                to_delete.append(key[4:-9])

        # delete everything related to all the jobs to delete
        print 'doing deletion of', to_delete
        for uid in to_delete:
            print 'delete', uid
            job = JobObj({'uid': uid})
            d = job.directory
            if d and len(d) > 10:
                subprocess.Popen(['rm', '-rf', d], shell=False).communicate()
            keys = r.keys('job:%s*' % uid)
            if keys:
                r.delete(*keys)
            keys = r.keys('log:%s*' % uid)
            if keys:
                r.delete(*keys)

        return

    jobkey = 'job:%s' % uid
    if not r.keys(jobkey):
        return

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


if __name__ == '__main__':
    while True:
        # trigger a purge every hour
        qlog.put({'cmd': 'purge', 'uid': 'moij'})
        for log in qlog.consume(timeout=3600):
            loop_handle(log)
        # sleep only 1 second if we keep asking break
        sleep(1)

