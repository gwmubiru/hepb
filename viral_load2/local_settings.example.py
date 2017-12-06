import db_engines
SESSION_COOKIE_AGE = 900
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'vl2',
        'USER': 'vl2',
        'PASSWORD': 'vl2',
        'HOST': '',
        'PORT': '',
    },
    'old_db': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'db_name',
        'USER': 'user',
        'PASSWORD': 'secret',
        'HOST': '',
        'PORT': '',
    }
}