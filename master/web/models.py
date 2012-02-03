from sqlalchemy import Column, Integer, String, Boolean
from web.database import Base, init_db
from web.config import config
from time import time
from uuid import uuid4
from os.path import join, dirname

class Job(Base):
    __tablename__ = 'job'
    id = Column(Integer, primary_key=True)
    uid = Column(String(64))
    package_version = Column(String(64))
    package_name = Column(String(128))
    package_title = Column(String(128))
    package_permissions = Column(String(2048))
    package_orientation = Column(String(16))
    emails = Column(String(2048))
    is_release = Column(Boolean)
    modules = Column(String(1024))
    dt_added = Column(Integer)
    dt_started = Column(Integer)
    dt_done = Column(Integer)
    is_started = Column(Boolean)
    is_done = Column(Boolean)
    is_failed = Column(Boolean)
    fail_message = Column(String(1024))
    have_icon = Column(Boolean)
    have_presplash = Column(Boolean)
    data_ext = Column(String(8))
    apk = Column(String(128))
    build_status = Column(String(64))

    def __init__(self):
        self.uid = str(uuid4())
        self.dt_added = time()
        self.dt_started = self.dt_done = 0
        self.have_icon = self.have_presplash = False
        self.is_release = False
        self.is_done = 0

    @property
    def directory(self):
        return join(dirname(__file__), '..','jobs', self.uid)

    @property
    def data_fn(self):
        return join(self.directory, 'data%s' % self.data_ext)

    @property
    def icon_fn(self):
        return join(self.directory, 'icon.png')

    @property
    def presplash_fn(self):
        return join(self.directory, 'presplash.png')

    @property
    def apk_fn(self):
        return join(self.directory, self.apk)

    def notify(self):
        if len(self.emails) == 0:
            return
        import subprocess
        status = 'failed build' if self.is_failed else 'finished'
        subject = '[p4a] Build %s, version %s %s' % (
            self.package_title,
            self.package_version,
            status)
        if self.is_failed:
            content = ('Hi,\n\nYour package %s failed to build.\n\n'
                    'Informations: %s\n\nP4A Build Cloud.') % (
                self.package_title,
                '%s/job/%s' % (config.get('www', 'baseurl'),self.uid))
        else:
            content = ('Hi,\n\nYour package %s is available.\n\n'
                    'APK: %s\nInformations: %s\n\nEnjoy,\n\nP4A Build Cloud.') % (
                self.package_title,
                '%s/download/%s/%s' % (config.get('www', 'baseurl'),
                    self.uid, self.apk),
                '%s/job/%s' % (config.get('www', 'baseurl'),self.uid))

        for email in self.emails.split():
            cmd = ['mail', '-s', subject, '-a', 'From: p4a-noreply@kivy.org',
                    email]
            p = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE)
            p.stdin.write(content)
            p.stdin.close()
            p.communicate()

class JobLog(Base):
    __tablename__ = 'joblog'
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer)
    msg = Column(String(80))

init_db()

