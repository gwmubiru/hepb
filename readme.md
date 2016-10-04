
sudo apt-get install mysql-server-5.6
$ sudo adduser vl

$ su vl

sudo apt-get install libmysqlclient-dev build-essential autoconf libtool pkg-config python-opengl python-imaging python-pyrex python-pyside.qtopengl idle-python2.7 qt4-dev-tools qt4-designer libqtgui4 libqtcore4 libqt4-xml libqt4-test libqt4-script libqt4-network libqt4-dbus python-qt4 python-qt4-gl libgle3 python-dev

$ sudo apt-get install python-pip

$ sudo apt-get install nodejs

$ sudo apt-get install npm

$ sudo npm install -g bower

$ sudo ln -s /usr/bin/nodejs /usr/bin/node --- in case /usr/bin/env is missing

$ sudo pip install virtualenv virtualenvwrapper

$ echo "export WORKON_HOME=~/Env" >> ~/.bashrc
$ echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bashrc


$ source ~/.bashrc

$ mkvirtualenv viral_load2 #Creates VM and activates it;; use deactivate to get out and workon vl_vm to go back on

$

$ cd viral_load2/viral_load2/

$ pip install -r requirements.txt

$ bower update

$ cp local_settings.example.py local_settings.py

$ vi local_settings.py

recv() failed (104: Connection reset by peer)
--
http://stackoverflow.com/questions/22697584/nginx-uwsgi-104-connection-reset-by-peer-while-reading-response-header-from-u

git clone https://github.com/CHAIUganda/viral_load2.git

CREATE DATABASE vldb character set utf8 collate utf8_general_ci;

CREATE USER 'vl'@'localhost' IDENTIFIED BY 'vlpass';

GRANT ALL PRIVILEGES ON vldb . * TO 'vl'@'localhost';

$ mysqldump -u username -p db | gzip -c > db.sql.gz

$ zcat db.sql.gz | mysql -u username -p db_name -f



$ set DB

$ ./manage.py migrate



sudo pip install uwsgi





sudo mkdir -p /etc/uwsgi/sites
cd /etc/uwsgi/sites


sudo vi vl.ini

		[uwsgi]
		project = project_folder
		base = /home/user

		chdir = %(base)/%(project)
		home = %(base)/Env/%(project)
		module = %(project).wsgi:application

		master = true
		processes = 5

		socket = %(base)/%(project)/%(project).sock
		chmod-socket = 664
		vacuum = true

sudo vi /etc/init/uwsgi.conf

		description "uWSGI application server in Emperor mode"

		start on runlevel [2345]
		stop on runlevel [!2345]

		setuid user
		setgid www-data

		exec /usr/local/bin/uwsgi --emperor /etc/uwsgi/sites



sudo vi /etc/nginx/sites-available/viral_load2

		server {
		    listen 80;
		    listen ip;

		    location = /favicon.ico { access_log off; log_not_found off; }
		    location /static/ {
		        root /home/user/firstsite;
		    }

		    location / {
		        include         uwsgi_params;
		        uwsgi_pass      unix:/home/user/firstsite/firstsite.sock;
		    }
		}


sudo ln -s /etc/nginx/sites-available/viral_load2 /etc/nginx/sites-enabled


sudo service nginx configtest

sudo service nginx restart

sudo service uwsgi start


./manage.py collectstatic


uwsgi --http :3333 --home /home/vl/Env/viral_load2 --chdir /home/vl/viral_load2 -w viral_load2.wsgi





