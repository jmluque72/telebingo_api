# -*- coding: utf-8 -*-
import os
from subprocess import call
import tempfile

from django.utils import timezone


PROD_PATH = '/home/liricus/webapps/agencia24/src/'
DESA_PATH = '/home/liricus/webapps/agencia24desa/src/'
PYTHON_PATH = '../bin/python2.7'

ACTIVATE_THIS_PATH = "../bin/activate_this.py"

FROM = timezone.datetime(2016,05,20).isoformat()
TO =   timezone.datetime(2016,05,25).isoformat()

import os
import shlex
from subprocess import Popen, PIPE


def activate_enviroment(path):
    os.chdir(path)
    activate_this_file = os.path.join(path, ACTIVATE_THIS_PATH)
    execfile(activate_this_file, dict(__file__=activate_this_file))


def execute_in_virtualenv(virtualenv_path, dump, commands):
    '''Execute Python code in a virtualenv, return its stdout and stderr.'''
    command_template = '/bin/bash -c "source {}/bin/activate && python {} && python -"'
    command = shlex.split(command_template.format(virtualenv_path, dump))
    process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=False)
    return process.communicate(commands)


def copy_draws(_from, _to):
    if isinstance(_from, timezone.datetime):
        _from = _from.isoformat()
    if isinstance(_to, timezone.datetime):
        _to = _to.isoformat()

    #activate_enviroment(PROD_PATH)

    tmp = tempfile.NamedTemporaryFile(delete=True, suffix='.json')
    try:
        os.chdir(PROD_PATH)
        #python_path = os.path.join(PROD_PATH, PYTHON_PATH)
        #call([python_path, 'manage.py', 'dump_object', 'pet.basedraw',
        #      '--query \'{"date_draw__range": ("%s", "%s")}\'' %(_from, _to)], stdout=tmp)

        from textwrap import dedent
        commands = dedent(r'''''')
        dump = 'manage.py dump_object pet.basedraw --query \'{"date_draw__range": ("%s", "%s")}\' > %s' %(_from, _to, tmp.name)
        stdout, stderr = execute_in_virtualenv('/home/liricus/webapps/agencia24/', dump, commands)

        with open(tmp.name, 'r') as fin:
            import logging
            logger = logging.getLogger('agencia24_default')
            logger.debug(fin.read())

        #activate_enviroment(DESA_PATH)
        os.chdir(DESA_PATH)
        #python_path = os.path.join(PROD_PATH, PYTHON_PATH)
        #call([python_path, 'manage.py', 'loaddata', tmp.name])
        dump = 'manage.py loaddata %s' %tmp.name
        stdout, stderr = execute_in_virtualenv('/home/liricus/webapps/agencia24desa/', dump, commands)

    finally:
        tmp.close()  # deletes the file


if __name__ == '__main__':
    copy_draws(FROM, TO)
