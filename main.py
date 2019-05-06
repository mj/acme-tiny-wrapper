#!/usr/bin/python

# apt-get install python-dateutil
# pip install pytz

import argparse
import getpass
import sys
import os
import imp
import subprocess
from dateutil import parser as dateparser
import datetime
import pytz
from ConfigParser import SafeConfigParser
from urllib2 import urlopen
import logging

class handler:
    config = {
        'certdir': '/home/certs/crt',
        'keydir': '/home/certs/key',
        'csrdir': '/home/certs/csr',
        'spooldir': '/home/certs/spool',
        'challengedir': '/var/www/acme-challenges/',
        'account-key': '/home/certs/key/account.key',
        'acmedir': '/usr/local/bin/', # the directory where acme_tiny.py resides
        'user': 'certs',
        'debug': False,
        'openssl': '/usr/bin/openssl',
        'renewal-threshold': 7,
    }

    def __init__(self, config):
        if config:
            parser = SafeConfigParser()
            parser.readfp(config)
            if parser.items('main'):
                for (name, value) in parser.items('main'):
                    self.config[name] = value

        if not self.config['debug']:
            # Hide traceback unless we are in debug mode
            sys.tracebacklimit = 0

        if getpass.getuser() != self.config['user']:
            raise RuntimeError('This program must be run as user ' + self.config['user'] + '.')

    def get_expiry(self, crt):
        cmd = [self.config['openssl'], "x509", "-in", crt, "-noout", "-enddate"]
        proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

        out, err = proc.communicate()

        if proc.returncode != 0:
            raise IOError("OpenSSL error: {0} " . format(err))

        return dateparser.parse(out[9:])

    def renew(self, domain):
        crt = os.path.join(self.config['certdir'], domain + '.crt')
        csr = os.path.join(self.config['csrdir'], domain + '.csr')

        if not os.path.isfile(crt):
            raise RuntimeError('There does not appear to be a certificate for ' + domain + ': No such file or directory ' + crt)

        expiry = self.get_expiry(crt)

        if not expiry:
            raise RuntimeError('Unable to determine expiry for the certificate in ' + crt)

        threshold = int(self.config['renewal-threshold'])

        # There is probably some timezone mess involved here that I'm 
        # unaware now. This Shouldn't really matter though as long as the
        # threshold isn't too tight.
        if expiry >= pytz.utc.localize(datetime.datetime.now() + datetime.timedelta(days = threshold)):
            print 'Skipping renewal for ' + domain + ' because expiry is more than ' + str(threshold) + ' days away.'
            return

        signed_crt = self.get_crt(csr, domain)
        intermediate = self.get_intermediate()

        with open(crt, 'w') as f:
            f.write(signed_crt)

            if intermediate is not None:
                with open(intermediate) as f2:
                    f.write(f2.read())
                f2.close()

            f.close()

        self.trigger_reload()

    def create(self, domain):
        print 'Creating certificate hasn\'t been implemeneted yet.'
        print

    def get_crt(self, csr, domain):
        logger = logging.getLogger('acme-tiny-wrapper')

        handler = logging.StreamHandler()
        handler.setLevel(logging.ERROR)
        formatter = logging.Formatter('Message from acme-tiny: %(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(logger)

        try:
            (file, pathname, description) = imp.find_module('acme_tiny', [self.config['acmedir']])
        except ImportError:
            raise RuntimeError('Unable to find acme-tiny in ' + self.config['acmedir'])

        if file is None:
            raise RuntimeError('Unable to find acme-tiny in ' + self.config['acmedir'])

        try:            
            acme_tiny = imp.load_module('acme_tiny', file, pathname, description)
        finally:
            file.close()

        try:
            return acme_tiny.get_crt(self.config['account-key'], csr, self.config['challengedir'], log = logger)
        except Exception, e:
            raise RuntimeError('Issuing certificate for ' + domain + ' failed: ' + str(e))

    def get_intermediate(self):
        url = 'https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem'
        crt = os.path.join(self.config['certdir'], 'lets-encrypt-x3-cross-signed.pem')

        if os.path.isfile(crt):
            return crt

        try:
            resp = urlopen(url)
            with open(crt, 'wb') as f:
                f.write(resp.read())
                f.close()
        except IOError:
            return None

        return crt

    def trigger_reload(self):
        open(self.config['spooldir'] + '/reload-webserver', 'a').close()

def main():
    parser = argparse.ArgumentParser(description = 'Manage Let\'s Encrypt certificates')
    parser.add_argument('--config', type = file)
    parser.add_argument('action', help = 'What to do', choices = ['create', 'renew'])
    parser.add_argument('domain', help = 'Domain name')

    args = parser.parse_args()

    h = handler(args.config)
    method = getattr(h, args.action)
    method(args.domain)

if __name__ == "__main__":
    main()
