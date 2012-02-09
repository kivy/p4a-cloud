__all__ = ('read_job', 'read_logs')


import subprocess
from os.path import dirname, join, realpath
from web.config import config, r

class QueryDict(dict):
    # taken from kivy
    def __getattr__(self, attr):
        try:
            return self.__getitem__(attr)
        except KeyError:
            try:
                return super(QueryDict, self).__getattr__(attr)
            except AttributeError:
                raise KeyError(attr)

    def __setattr__(self, attr, value):
        self.__setitem__(attr, value)


class JobObj(QueryDict):
    @property
    def directory(self):
        return realpath(join(dirname(__file__), '..', 'jobs', self.uid))

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
        status = 'failed build' if self.is_failed == '1' else 'finished'
        subject = '[p4a] Build %s, version %s %s' % (
            self.package_title,
            self.package_version,
            status)
        if self.is_failed == '1':
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

def read_entry(basekey, cls=QueryDict, *keyswanted):
    keys = r.keys('%s*' % basekey)
    entry = cls()
    for key in keyswanted:
        entry[key] = None
    for key in keys:
        skey = key[len(basekey):]
        if keyswanted and skey not in keyswanted:
            continue
        entry[skey] = r.get(key)
    return entry

def read_logs(uid):
    return read_entry('log:%s:' % uid).values()

def read_job(uid, *keys):
    if not r.keys('job:%s' % uid):
        return None
    job = read_entry('job:%s:' % uid, JobObj, *keys)
    job['uid'] = uid
    return job

