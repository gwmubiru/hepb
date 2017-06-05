import db_engines
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