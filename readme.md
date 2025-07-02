
$ sudo apt-get install mysql-server-5.6

$ sudo adduser vl

$ sudo apt-get install libmysqlclient-dev build-essential autoconf libtool pkg-config python-opengl python-imaging python-pyrex python-pyside.qtopengl idle-python2.7 qt4-dev-tools qt4-designer libqtgui4 libqtcore4 libqt4-xml libqt4-test libqt4-script libqt4-network libqt4-dbus python-qt4 python-qt4-gl libgle3 python-dev

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

$ git clone https://github.com/CHAIUganda/viral_load2

$ cd viral_load2/viral_load2/

$ pip install -r requirements.txt

$ bower update

$ cp local_settings.example.py local_settings.py

$ vi local_settings.py

recv() failed (104: Connection reset by peer)
--
http://stackoverflow.com/questions/22697584/nginx-uwsgi-104-connection-reset-by-peer-while-reading-response-header-from-u


CREATE DATABASE vldb character set utf8 collate utf8_general_ci;

CREATE USER 'vl'@'localhost' IDENTIFIED BY 'vlpass';

GRANT ALL PRIVILEGES ON vldb . * TO 'vl'@'localhost';

$ mysqldump -u username -p db | gzip -c > db.sql.gz

$ zcat db.sql.gz | mysql -u username -p db_name -f



$ set DB

$ ./manage.py migrate
$ ./manage.py loaddata initial_data.json
$ ./manage.py transfer_users
$ ./manage.py transfer_facility_stuff



sudo pip install uwsgi
sudo apt-get install nginx




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
		buffer-size = 65535

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

//if uwsgi fails to start, create -- /etc/systemd/system/uwsgi.service

vi /etc/systemd/system/uwsgi.service 
[Unit]
Description=uWSGI Emperor service
After=syslog.target

[Service]
ExecStart=/usr/local/bin/uwsgi --emperor /etc/uwsgi/sites
Restart=always
KillSignal=SIGQUIT
Type=notify
StandardError=syslog
NotifyAccess=all

[Install]
WantedBy=multi-user.target




./manage.py collectstatic


uwsgi --http :3333 --home /home/vl/Env/viral_load2 --chdir /home/vl/viral_load2 -w viral_load2.wsgi


python manage.py createsuperuser




DELIMITER //
CREATE TRIGGER create_vl_sample_id
BEFORE INSERT
   ON vl_samples FOR EACH ROW

BEGIN

SET NEW.vl_sample_id = (SELECT CONCAT((SELECT IFNULL( (SELECT LPAD(SUBSTRING(vl_sample_id,1,6)+1,6,'0') FROM vl_samples WHERE MONTH(created_at)=MONTH(CURRENT_TIMESTAMP()) and YEAR(created_at)=YEAR(CURRENT_TIMESTAMP()) ORDER BY id DESC LIMIT 1), '000001')),"/", DATE_FORMAT(CURRENT_TIMESTAMP, "%y"),DATE_FORMAT(CURRENT_TIMESTAMP, "%m")) AS new_sample_id);

END;//

DELIMITER ;