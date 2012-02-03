
import threading
from web import app
from web.apps.frontend import frontend

app.register_blueprint(frontend)


def run_log_queue():
    from web.config import config
    from hotqueue import HotQueue
    from web.models import Job, JobLog
    from web.database import db_session

    # start a thread for listing qlog
    qlog = HotQueue(
        'joblog',
        host=config.get('hotqueue', 'host'),
        port=config.getint('hotqueue', 'port'),
        db=config.getint('hotqueue', 'db'),
        password=config.get('hotqueue', 'password'))


    def poll_qlog():

        cache = {}

        for log in qlog.consume():
            if 'cmd' not in log or 'uid' not in log:
                continue
            cmd = log['cmd']
            uid = log['uid']

            if uid in cache:
                job = cache[uid]
            else:
                job = Job.query.filter_by(uid=uid).first()
                if job is None:
                    cache[uid] = None
                    continue

            if job is None:
                continue

            if cmd == 'status':
                job.build_status = log['msg']
                db_session.commit()
            elif cmd == 'exception':
                job = Job.query.filter_by(uid=uid).first()
                if not job:
                    continue
                job.build_status = '[1/1] Error'
                job.is_failed = True
                job.fail_message = log['msg']
                jl = JobLog()
                jl.job_id = job.id
                jl.msg = log['msg'].decode('utf8')
                db_session.add(jl)
                db_session.commit()

                job.notify()
            elif cmd == 'log':
                jl = JobLog()
                jl.job_id = job.id
                jl.msg = log['line'].decode('utf8')
                db_session.add(jl)
                db_session.commit()



    thread = threading.Thread(target=poll_qlog)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    run_log_queue()
    app.debug = True
    app.run('0.0.0.0')

