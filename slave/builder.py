import re
import socket
from copy import copy
from os import mkdir, environ
from os.path import dirname, join, realpath, exists, basename
from hotqueue import HotQueue
from ConfigParser import ConfigParser
from time import sleep

buildenv = copy(environ)
environ.pop('http_proxy', None)

import subprocess
import requests

# reading the configuration
hostname = socket.gethostname()
config = ConfigParser()
config.read(join(dirname(__file__), 'config.cfg'))

# start the queue
qjob = HotQueue(
    'jobsubmit',
    host=config.get('hotqueue', 'host'),
    port=config.getint('hotqueue', 'port'),
    db=config.getint('hotqueue', 'db'),
    password=config.get('hotqueue', 'password'))

qlog = HotQueue(
    'joblog',
    host=config.get('hotqueue', 'host'),
    port=config.getint('hotqueue', 'port'),
    db=config.getint('hotqueue', 'db'),
    password=config.get('hotqueue', 'password'))

# put a hello world message
qlog.put({'cmd': 'alive', 'host': hostname})

# create the job directory if not exist
root_dir = realpath(join(dirname(__file__), 'jobs'))
try:
    mkdir(root_dir)
except:
    pass

# checkout and clean the python-for-android project
build_dir = realpath(join(dirname(__file__), 'python-for-android'))
dist_dir = join(build_dir, 'dist', 'default')
if not exists(build_dir):
    subprocess.Popen(['git', 'clone',
        'git://github.com/kivy/python-for-android'], shell=False).communicate()
else:
    subprocess.Popen(['git', 'clean', '-dxf'], shell=False,
        cwd=build_dir).communicate()
    subprocess.Popen(['git', 'pull', 'origin', 'master'], shell=False,
        cwd=build_dir).communicate()

base_maxstatus = 10
max_status = base_maxstatus
id_status = 0
def status(job, message):
    global id_status
    id_status += 1
    print job['uid'], message
    message = '[%d/%d] ' % (id_status, max_status) + message
    qlog.put({'cmd': 'status', 'uid': job['uid'], 'msg': message, 'host':
        hostname})
    qlog.put({'cmd': 'log', 'uid': job['uid'], 'line': message, 'host':
        hostname})

def command(job, command, cwd=None):
    global max_status
    process = subprocess.Popen(command, shell=False, cwd=cwd,
            stderr=subprocess.STDOUT, stdout=subprocess.PIPE, env=buildenv)
    lines = []
    while process.poll() is None:
        line = process.stdout.readline()
        if not line:
            break
        line = line.rstrip('\r\n')
        lines.append(line)
        lines = lines[-100:]
        #qlog.put({'cmd': 'log', 'uid': job['uid'], 'line': line})
        print job['uid'], process.returncode, line

        # send progressive distribution information
        if 'Dependency order' in line:
            groups = re.search('Dependency order is (.*) \(computed\)', line)
            if groups:
                groups = groups.groups()[0].split()
                max_status = base_maxstatus + len(groups)
        if 'Run get packages' in line:
            status(job, 'Downloading packages')
        elif 'Run prebuild' in line:
            status(job, 'Prebuild packages')
        elif 'Run build' in line:
            status(job, 'Building packages')
        elif 'Run postbuild' in line:
            status(job, 'Postbuild packages')
        elif 'Run distribute' in line:
            status(job, 'Create distribution')
        elif 'Call build_' in line:
            groups = re.search('build_(\w+)', line)
            if groups:
                package = groups.groups()[0]
                status(job, 'Build ' + package)

    process.communicate()

    print process.returncode, command
    if process.returncode != 0:
        qlog.put({'cmd': 'status', 'uid': job['uid'],
            'msg': 'Error while executing %r' % command,
            'host': hostname})
        raise Exception('Error on %r.\n\n%s' % (command, '\n'.join(lines)))

def builder(job_dir, **job):
    # got a job to do
    uid = job['uid']

    app_dir = join(job_dir, 'app')
    mkdir(app_dir)

    # do the job here
    url_base = config.get('www', 'url')

    # get data
    url_data = url_base + '/api/data/' + uid
    r = requests.get(url_data)
    r.raise_for_status()
    data_fn = join(job_dir, 'data.zip')
    with open(data_fn, 'wb') as fd:
        fd.write(r.content)

    # icon ?
    if job['have_icon'] == '1':
        url_icon = url_base + '/api/icon/' + uid
        r = requests.get(url_icon)
        r.raise_for_status()
        icon_fn = join(job_dir, 'icon.png')
        with open(icon_fn, 'wb') as fd:
            fd.write(r.content)

    # presplash ?
    if job['have_presplash'] == '1':
        url_presplash = url_base + '/api/presplash/' + uid
        r = requests.get(url_presplash)
        r.raise_for_status()
        presplash_fn = join(job_dir, 'presplash.png')
        with open(presplash_fn, 'wb') as fd:
            fd.write(r.content)

    # decompress
    command(job, ['unzip', '-d', app_dir, data_fn])

    # build distribution
    status(job, 'Build distribution')
    command(job, ['git', 'clean', '-dxf'], build_dir)
    command(job, ['./distribute.sh', '-m', job['modules']], build_dir)

    # build the package
    status(job, 'Build apk')
    build = ['./build.py',
        '--package', job['package_name'],
        '--name', job['package_title'],
        '--version', job['package_version'],
        '--private', app_dir,
        '--orientation', job['package_orientation']]
    if job['have_icon'] == '1':
        build.append('--icon')
        build.append(icon_fn)
    if job['have_presplash'] == '1':
        build.append('--presplash')
        build.append(presplash_fn)
    if job['package_permissions']:
        for permission in job['package_permissions'].split(' '):
            build.append('--permission')
            build.append(permission)
    build.append(job['mode'])
    command(job, build, dist_dir)

    # get apk name
    versioned_name = job['package_title'].replace(' ', '').replace('\'', '') + \
        '-' + job['package_version']
    apk_fn = join(dist_dir, 'bin', '%s-%s.apk' % (versioned_name,
        'release-unsigned' if job['mode'] == 'release' else 'debug'))

    # job done, upload the apk
    status(job, 'Upload %s' % basename(apk_fn))
    with open(apk_fn, 'rb') as fd:
        files = {'file': (basename(apk_fn), fd)}
        count = 5
        while count:
            try:
                status(job, 'Uploading (%d remaining)' % count)
                r = requests.post(url_base + '/api/push/' + uid, files=files)
            except:
                count -= 1
                status(job, 'Upload failed (%d remaining)' % count)
                if not count:
                    raise
                sleep(5)
                continue

            r.raise_for_status()
            break

    status(job, 'Done')

# === go !
print '== Ready to build!'
while True:
    qlog.put({'cmd': 'available', 'host': hostname})
    task = qjob.get(timeout=5, block=True)
    if task is None:
        continue
    qlog.put({'cmd': 'busy', 'host': hostname})
    uid = task['uid']
    try:
        id_status = 0
        max_status = base_maxstatus
        status(task, 'Initialize job')
        # create a directory
        job_dir = realpath(join(root_dir, uid))
        mkdir(job_dir)
        qlog.put({'cmd': 'start', 'uid': uid, 'host': hostname})
        builder(job_dir, **task)
        qlog.put({'cmd': 'done', 'uid': uid, 'host': hostname})
    except Exception, e:
        print 'Got exception', e
        import traceback
        traceback.print_exc()
        qlog.put({'cmd': 'exception', 'uid': uid, 'msg': str(e), 'host':
            hostname})
    finally:
        # just to be entirely sure sure sure
        if len(uid) > 10 and not '.' in uid and job_dir.endswith(uid):
            subprocess.Popen(['rm', '-rf', job_dir], shell=False).communicate()

