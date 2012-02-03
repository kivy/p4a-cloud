'''
Frontend module
'''

__all__ = ('frontend', )

from flask import Blueprint, render_template, url_for, redirect, abort, \
    send_file, request, make_response, jsonify
from web.database import db_session
from web.models import Job, JobLog
from werkzeug import secure_filename
from web.config import qjob
from sqlalchemy.sql import desc
from os.path import realpath
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
    job = Job.query.filter_by(uid=uid).first()
    if not job:
        return redirect(url_for('frontend.index'))
    joblog = JobLog.query.filter_by(job_id=job.id).order_by(desc(JobLog.id)).limit(20)
    joblog = list(reversed(joblog[:]))
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
    job = Job.query.filter_by(uid=uid).first()
    if not job:
        abort(404)

    # delte job directory
    d = realpath(job.directory)
    if d and len(d) > 10:
        subprocess.Popen(['rm', '-rf', d], shell=False).communicate()

    # delete associated logs and job
    db_session.query(JobLog).filter_by(job_id=job.id).delete()
    db_session.delete(job)
    db_session.commit()
    db_session.flush()

    return redirect(url_for('frontend.index'))


@frontend.route('/api/data/<uid>')
def jobdata(uid):
    job = Job.query.filter_by(uid=uid).first()
    if not job:
        return abort(404)
    job.is_started = True
    job.dt_started = time()
    db_session.commit()
    return send_file(job.data_fn)

@frontend.route('/api/icon/<uid>')
def jobicon(uid):
    job = Job.query.filter_by(uid=uid).first()
    if not job or not job.have_icon:
        return abort(404)
    return send_file(job.icon_fn)

@frontend.route('/api/presplash/<uid>')
def jobpresplash(uid):
    job = Job.query.filter_by(uid=uid).first()
    if not job or not job.have_presplash:
        return abort(404)
    return send_file(job.presplash_fn)

@frontend.route('/api/push/<uid>', methods=['POST'])
def jobpush(uid):
    job = Job.query.filter_by(uid=uid).first()
    if not job:
        return abort(404)
    file = request.files['file']
    if file and file.filename.rsplit('.', 1)[-1] == 'apk':
        filename = secure_filename(file.filename)
        file.save(join(job.directory, filename))
        job.apk = filename
        job.is_done = True
        job.dt_done = time()
        db_session.commit()

        try:
            job.notify()
        except:
            pass
        return make_response('done')
    else:
        return abort(403)

@frontend.route('/download/<uid>/<apk>')
def download(uid, apk):
    job = Job.query.filter_by(uid=uid).first()
    if not job or job.apk is None or job.is_done is False:
        return abort(404)
    return send_file(job.apk_fn)

@frontend.route('/')
def index():
    form = JobForm()
    return render_template('frontend/index.html', form=form)

def csplit(s):
    return ' '.join([x for x in re.split(r'[.; ]', s) if len(x)])

@frontend.route('/submit', methods=['POST'])
def submit():
    form = JobForm()
    if form.validate_on_submit():
        job = Job()

        fn = secure_filename(form.directory.file.filename)
        ext = splitext(fn)[-1]
        if splitext(fn)[-1] not in (
                '.zip'):#, '.tbz', '.tar.gz', '.tbz2', '.tar.bz2'):
            return render_template('frontend/index.html', form=form,
                    error='Invalid application directory package')

        # create the job directory
        d = job.directory
        mkdir(d)
        form.directory.file.save(join(d, 'data%s' % ext))

        if form.package_presplash.file:
            form.package_presplash.file.save(job.presplash_fn)
            job.have_presplash = True

        if form.package_icon.file:
            form.package_icon.file.save(job.icon_fn)
            job.have_icon = True

        # add in the database
        job.package_name = form.package_name.data
        job.package_version = form.package_version.data
        job.package_title = form.package_title.data
        job.package_orientation = form.package_orientation.data
        job.package_permissions = form.package_permissions.data
        job.modules = form.modules.data
        job.emails = form.emails.data
        if form.release.data:
            job.is_release = True
        job.data_ext = ext
        db_session.add(job)
        db_session.commit()

        # submit a job in reddis
        print 'RELEASE?', job.is_release
        raise Exception()
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
            'mode': 'release' if job.is_release else 'debug',
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

