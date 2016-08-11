import db_engines
DATABASES = {
    'default': {
        'ENGINE': db_engines.gears.get(os.environ.get('DB_ENGINE'),'django.db.backends.mysql'),
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
    'old_db': {
        'ENGINE': db_engines.gears.get(os.environ.get('DB_ENGINE'),'django.db.backends.mysql'),
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}