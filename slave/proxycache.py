import BaseHTTPServer
import hashlib
import os
import requests
import urllib2

cache_ext = ('.zip', '.tgz', '.tbz2', '.tar.gz', '.tar.bz2')

class CacheHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def allowed(self, p):
        for ext in cache_ext:
            if p.endswith(ext):
                return True
    def do_GET(self):
        if self.allowed(self.path):
            m = hashlib.md5()
            m.update(self.path)
            cache_filename = os.path.join('cache', m.hexdigest())
            if os.path.exists(cache_filename):
                print "Cache hit", self.path
                with open(cache_filename) as fd:
                    data = fd.read()
                code = 200
            else:
                print "Cache miss", self.path
                #r = requests.get(self.path)
                #data = r.raw.read()
                #code = r.status_code
                r = urllib2.urlopen(self.path)
                data = r.read()
                code = r.getcode()
                with open(cache_filename, 'wb') as fd:
                    fd.write(data)
        else:
            #r = requests.get(self.path)
            #data = r.raw.read()
            #code = r.status_code
            r = urllib2.urlopen(self.path)
            data = r.read()
            code = r.getcode()

        self.send_response(code)
        self.end_headers()
        self.wfile.write(data)

def run():
    server_address = ('', 8000)
    httpd = BaseHTTPServer.HTTPServer(server_address, CacheHandler)
    httpd.serve_forever()

if __name__ == '__main__':
    run()
