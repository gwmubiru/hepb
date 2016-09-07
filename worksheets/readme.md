sudo adduser vl

su vl

sudo apt-get install python-pip

sudo pip install virtualenv virtualenvwrapper

echo "export WORKON_HOME=~/Env" >> ~/.bashrc
echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bashrc


source ~/.bashrc

mkvirtualenv vl_vm #Creates VM and activates it;; use deactivate to get out and workon vl_vm to go back on

git clone https://github.com/CHAIUganda/viral_load2.git

CREATE DATABASE vldb character set utf8 collate utf8_general_ci;

CREATE USER 'vl'@'localhost' IDENTIFIED BY 'vlpass';

GRANT ALL PRIVILEGES ON vldb . * TO 'vl'@'localhost';

$ mysqldump -u username -p db | gzip -c > db.sql.gz

$ zcat db.sql.gz | mysql -u username -p db_name -f

$ cd viral_load2/viral_load2/

$ cp local_settings.example.py local_settings.py

$ vi local_settings.py

$ set DB

$ ./manage.py migrate

