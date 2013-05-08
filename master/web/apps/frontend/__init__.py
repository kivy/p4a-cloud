'''
Frontend module
'''

__all__ = ('frontend', )

from flask import Blueprint, render_template, url_for, redirect, abort, \
    send_file, request, make_response, jsonify
from web.job import read_job, read_logs, JobObj
from werkzeug import secure_filename
from web.config import qjob, r
from os.path import exists
from uuid import uuid4
import subprocess
import re

from time import time
from os import mkdir
from os.path import join, splitext
from flaskext.wtf import Form, TextField, SubmitField, validators, \
    FileField, SelectField, BooleanField

frontend = Blueprint('frontend', __name__, static_folder='static',
        static_url_path='/frontend/static', template_folder='templates')

class JobForm(Form):
    package_name = TextField('Package', [
        validators.Required(), validators.Length(min=3, max=128)],
        description='org.kivy.touchtracer')
    package_version = TextField('Version', [
        validators.Required(), validators.Length(min=1, max=64)],
        description='1.0')
    package_title = TextField('Name', [
        validators.Required(), validators.Length(min=1, max=128)],
        description='Touchtracer')
    modules = TextField('Modules',
        description='pil kivy')
    directory = FileField('Application zipped with main.py',
        description='''You must create a zip of your application directory
        containing main.py in the zip root.''')
    package_permissions = TextField('Permissions', [
        validators.Length(max=2048)],
        description='INTERNET')
    package_orientation = SelectField('Orientation', choices=[
        ('landscape', 'Landscape'),
        ('portrait', 'Portrait')], default='landscape')
    package_icon = FileField('Icon')
    package_presplash = FileField('Presplash')
    emails = TextField('Send notification to', [
        validators.Length(max=2048)],
        description='your@email.com')
    release = BooleanField('Release mode')
    submit = SubmitField('Submit')

@frontend.route('/job/<uid>')
def job(uid):
    job = read_job(uid)
    if job is None:
        return redirect(url_for('frontend.index'))

    # get the log associated to the job
    joblog = list(reversed(read_logs(uid)))
    progress = job.build_status
    if not progress:
        pprogress = 0
        ptotal = 1
        pcurrent = 0
        status = "Waiting a builder"
    else:
        try:
            progress, status = progress[1:].split(']', 1)
            pcurrent, ptotal = progress.split('/')
        except ValueError:
            status = job.build_status
            pcurrent = 1
            ptotal = 1
        pprogress = int((int(pcurrent) / float(ptotal)) * 100.)
        status = status.strip().rstrip('.').capitalize()
    return render_template('frontend/job.html', job=job, joblog=joblog,
            pcurrent=pcurrent, ptotal=ptotal, pprogress=pprogress,
            status=status)

@frontend.route('/job/<uid>/delete')
def delete(uid):
    job = read_job(uid, 'package_name')
    if not job:
        abort(404)

    # delte job directory
    d = job.directory
    if d and len(d) > 10:
        subprocess.Popen(['rm', '-rf', d], shell=False).communicate()

    keys = r.keys('job:%s*' % uid)
    if keys:
        r.delete(*keys)
    keys = r.keys('log:%s*' % uid)
    if keys:
        r.delete(*keys)

    return redirect(url_for('frontend.index'))

@frontend.route('/api/data/<uid>')
def jobdata(uid):
    job = read_job(uid, 'directory', 'data_ext')
    if not job:
        return abort(404)
    print job
    r.set('job:%s:dt_started' % uid, time())
    r.set('job:%s:is_started' % uid, 1)
    return send_file(job.data_fn)

@frontend.route('/api/icon/<uid>')
def jobicon(uid):
    job = read_job(uid, 'directory', 'have_icon')
    if not job or not job.have_icon or not exists(job.icon_fn):
        return abort(404)
    return send_file(job.icon_fn)

@frontend.route('/api/presplash/<uid>')
def jobpresplash(uid):
    job = read_job(uid, 'directory')
    if not job or not job.have_presplash or not exists(job.presplash_fn):
        return abort(404)
    return send_file(job.presplash_fn)

@frontend.route('/api/push/<uid>', methods=['POST'])
def jobpush(uid):
    job = read_job(uid)
    if not job:
        return abort(404)
    file = request.files['file']
    if file and file.filename.rsplit('.', 1)[-1] == 'apk':
        filename = secure_filename(file.filename)
        file.save(join(job.directory, filename))
        r.set('job:%s:apk' % uid, filename)
        r.set('job:%s:dt_done' % uid, time())
        r.set('job:%s:is_done' % uid, 1)

        try:
            job.notify()
        except:
            pass
        return make_response('done')
    else:
        return abort(403)

@frontend.route('/download/<uid>/<apk>')
def download(uid, apk):
    job = read_job(uid, 'apk', 'directory', 'dt_done')
    if not job or not job.apk or not job.dt_done:
        return abort(404)
    return send_file(job.apk_fn)

@frontend.route('/')
def index():
    form = JobForm()
    return render_template('frontend/index.html', form=form)

@frontend.route('/faq')
def faq():
    return render_template('frontend/faq.html')

@frontend.route('/about')
def about():
    return render_template('frontend/about.html')

@frontend.route('/status')
def status():
    key = qjob.key
    queue_len = qjob._HotQueue__redis.llen(key)

    hosts_last_alive = r.keys('host:*:last_alive')
    hosts = [x.split(':')[1] for x in hosts_last_alive]

    stats = {}
    for host in hosts:
        stats[host] = {
                'last_seen': int(time() - float(r.get('host:{}:last_alive'.format(host)))),
                'status': r.get('host:{}:status'.format(host))}

    return render_template('frontend/status.html', queue_len=queue_len,
            stats=stats)

def csplit(s):
    return ' '.join([x for x in re.split(r'[.; ]', s) if len(x)])

@frontend.route('/submit', methods=['POST'])
def submit():
    form = JobForm()
    if form.validate_on_submit():
        fn = secure_filename(form.directory.file.filename)
        ext = splitext(fn)[-1]
        if splitext(fn)[-1] not in (
                '.zip'):#, '.tbz', '.tar.gz', '.tbz2', '.tar.bz2'):
            return render_template('frontend/index.html', form=form,
                    error='Invalid application directory package')

        # create a job
        uid = str(uuid4())

        # fake job obj for getting path
        job = JobObj({'uid': uid})

        jobkey = 'job:%s' % uid
        basekey = jobkey + ':'
        r.set(basekey + 'dt_added', time())

        # create the job directory
        d = job.directory
        mkdir(d)
        form.directory.file.save(join(d, 'data%s' % ext))

        if form.package_presplash.file:
            form.package_presplash.file.save(job.presplash_fn)
            r.set(basekey + 'have_presplash', 1)
        else:
            r.set(basekey + 'have_presplash', 0)

        if form.package_icon.file:
            form.package_icon.file.save(job.icon_fn)
            r.set(basekey + 'have_icon', 1)
        else:
            r.set(basekey + 'have_icon', 0)

        # add in the database
        r.set(basekey + 'package_name', form.package_name.data)
        r.set(basekey + 'package_version', form.package_version.data)
        r.set(basekey + 'package_title', form.package_title.data)
        r.set(basekey + 'package_orientation', form.package_orientation.data)
        r.set(basekey + 'package_permissions', form.package_permissions.data)
        r.set(basekey + 'modules', form.modules.data)
        r.set(basekey + 'emails', form.emails.data)
        r.set(basekey + 'data_ext', ext)
        r.set(basekey + 'is_release', 1 if form.release.data else 0)
        r.set(basekey + 'build_status', '')
        r.set(basekey + 'is_failed', 0)
        r.set(basekey + 'is_started', 0)
        r.set(basekey + 'is_done', 0)
        r.set(basekey + 'apk', '')

        # creation finished
        r.set(jobkey, uid)

        # not optimized, but reread it.
        job = read_job(uid)

        # submit a job in reddis
        qjob.put({
            'uid': job.uid,
            'package_name': job.package_name,
            'package_title': job.package_title,
            'package_version': job.package_version,
            'package_orientation': job.package_orientation,
            'package_permissions': csplit(job.package_permissions),
            'emails': csplit(job.emails),
            'have_icon': job.have_icon,
            'have_presplash': job.have_presplash,
            'mode': 'release' if job.is_release == '1' else 'debug',
            'modules': csplit(job.modules)
        })

        if 'batch' in request.form:
            d = {'status': 'ok',
                'uid': job.uid,
                'url': url_for('frontend.job', uid=job.uid, _external=True)}
            return jsonify(**d)
        else:
            # redirect to the view job
            return redirect(url_for('frontend.job', uid=job.uid))

    return render_template('frontend/index.html', form=form)

