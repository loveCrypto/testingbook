import random
import re

from fabric.api import cd, env, local, run
from fabric.contrib.files import append, exists

REPO_URL = 'https://github.com/loveCrypto/testingbook'
NEWHOST = False
PORTNUMBER = False


def _get_a_free_port():
    global PORTNUMBER
    if not exists(f'~/service/gunicorn{env.host}'):
        result = run('uberspace-add-port -p tcp -f').stdout.strip()
        command = re.search(r"\d+", result)
        PORTNUMBER = command.group()


def _create_htaccess():
    if(PORTNUMBER):
        run(f'sed "s/PORTNUMBER/{PORTNUMBER}/g" deploy_tools/htaccess | \
            tee .htaccess')


def _register_gunicorn_as_service():
    if(PORTNUMBER):
        if not exists('~/service'):
            run('uberspace-setup-svscan')
        servicename = f'gunicorn{env.host}'
        folder = f'/var/www/virtual/{env.user}/{env.host}'
        gunicorn_path = f'{folder}/virtualenv/bin/gunicorn'
        run(f'uberspace-setup-service {servicename} {gunicorn_path} \
            --error-logfile - --reload  --chdir {folder} \
            --bind 127.0.0.1:{PORTNUMBER} superlists.wsgi:application')


def _register_subdomain():
    if not exists(f'/var/www/virtual/{env.user}/{env.host}'):
        run(f'uberspace-add-domain -d {env.host} -w')


def _get_latest_source():

    if exists('.git'):
        run('git fetch')
    else:
        run(f'git clone {REPO_URL} .')
        global NEWHOST
        NEWHOST = True
    current_commit = local('git log -n 1 --format=%H', capture=True)
    run(f'git reset --hard {current_commit}')


def _update_virtualenv():
    if not exists('virtualenv/bin/pip'):
        run(f'python3.6 -m venv virtualenv')
    run('./virtualenv/bin/pip install --upgrade pip')
    run('./virtualenv/bin/pip install -r requirements.txt')


def _create_or_update_dotenv():
    append('.env', 'DJANGO_DEBUG_FALSE=y')
    append('.env', f'SITENAME={env.host}')
    current_contents = run('cat .env')
    if 'DJANGO_SECRET_KEY' not in current_contents:
        new_secret = ''.join(random.SystemRandom().choices(
            'abcdefghijklmnopqrstuvwxyz0123456789', k=50
        ))
        append('.env', f'DJANGO_SECRET_KEY={new_secret}')


def _update_static_files():
    run('./virtualenv/bin/python manage.py collectstatic --noinput')


def _update_database():
    run('./virtualenv/bin/python manage.py migrate --noinput')


def deploy():
    site_folder = f'/var/www/virtual/{env.user}/{env.host}'
    run(f'mkdir -p {site_folder}')
    with cd(site_folder):
        _get_latest_source()
        _update_virtualenv()
        _create_or_update_dotenv()
        _update_static_files()
        _update_database()
        

def newhost():
    site_folder = f'/var/www/virtual/{env.user}/{env.host}'
    run(f'mkdir -p {site_folder}')
    with cd(site_folder):
        _get_a_free_port()
        _create_htaccess()
        _register_gunicorn_as_service()
        #_register_subdomain()
