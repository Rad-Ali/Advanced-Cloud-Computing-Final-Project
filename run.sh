#!/usr/bin/env bash

WORKDIR=$(cd "$(dirname "$0")" && pwd)
export WORKDIR


VENV=$(realpath "$PWD")/venv
if [[ ! -d $VENV ]]; then
    virtualenv -p python3 "$VENV" || python3 -m venv "$VENV"
fi

activate_venv() {
    # shellcheck source=/dev/null
    source "$WORKDIR/venv/bin/activate"
}

# Source code dependencies
echo "Installing dependencies"
activate_venv && pip3 install -r requirements.txt

activate_venv && python instance_setup.py

# Import all the necessary IP and DNS addresses
source env_variables.txt
chmod 600 "$PRIVATE_KEY_FILE"

# Even though we wait for the instance to be running in python, openssh takes some time to start.
# We check port 22 every 3s to see if sshd started on our instance, before trying to ssh into it.
SSH_IS_NOT_RUNNING=1
while [[ $SSH_IS_NOT_RUNNING -eq 1 ]]; do
    # if exit code of nc is 0, ssh started, else if it is 1, ssh is not started.
    nc -vzw 1 "$MASTER_IP" 22
    SSH_IS_NOT_RUNNING=$?
    if [[ $SSH_IS_NOT_RUNNING -eq 1 ]]; then
        echo "ssh not started yet, trying again in 3s..."; 
        sleep 3s;
    else
        echo "ssh started.";
    fi
done

# What is done here :
#    - Download and install the MYSQL Cluster to the master instance
#    - Set up environment variables
#    - Set up the config files
ssh -o "StrictHostKeyChecking no" -i "./$PRIVATE_KEY_FILE" ubuntu@"$MASTER_IP" << HERE
set -x 
sudo mkdir -p /opt/mysqlcluster/home
cd /opt/mysqlcluster/home
sudo wget -q http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz
sudo tar xf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz
sudo ln -s mysql-cluster-gpl-7.2.1-linux2.6-x86_64 mysqlc
cd ~
echo "export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc
export PATH=/opt/mysqlcluster/home/mysqlc/bin:\$PATH" > mysqlc.sh
sudo mv mysqlc.sh /etc/profile.d/mysqlc.sh
source /etc/profile.d/mysqlc.sh
sudo apt-get -qq update -y && sudo apt-get -qq install -y libncurses5
sudo mkdir -p /opt/mysqlcluster/deploy
cd /opt/mysqlcluster/deploy
sudo mkdir conf
sudo mkdir mysqld_data
sudo mkdir ndb_data
cd ~
echo "[mysqld]
ndbcluster
datadir=/opt/mysqlcluster/deploy/mysqld_data
basedir=/opt/mysqlcluster/home/mysqlc
bind-address=0.0.0.0
#bind-address=127.0.0.1
port=3306" > my.cnf
sudo mv my.cnf /opt/mysqlcluster/deploy/conf/my.cnf
echo "[ndb_mgmd]
hostname=$MASTER_DNS
datadir=/opt/mysqlcluster/deploy/ndb_data
nodeid=1

[ndbd default]
noofreplicas=3
datadir=/opt/mysqlcluster/deploy/ndb_data

[ndbd]
hostname=$SLAVE0_DNS
nodeid=3

[ndbd]
hostname=$SLAVE1_DNS
nodeid=4

[ndbd]
hostname=$SLAVE2_DNS
nodeid=5

[mysqld]
nodeid=50" > config.ini
sudo mv config.ini /opt/mysqlcluster/deploy/conf/config.ini
cd /opt/mysqlcluster/home/mysqlc
sudo scripts/mysql_install_db --no-defaults --datadir=/opt/mysqlcluster/deploy/mysqld_data
sudo /opt/mysqlcluster/home/mysqlc/bin/ndb_mgmd -f /opt/mysqlcluster/deploy/conf/config.ini --initial --configdir=/opt/mysqlcluster/deploy/conf/
HERE

slaves=($SLAVE0_IP $SLAVE1_IP $SLAVE2_IP)

# What is done here :
#    - Download and install the MYSQL Cluster to the slave instances
#    - Set up environment variables
#    - Set up the config files
#    - Start node
for ip in ${slaves[@]}; do
    ssh -o "StrictHostKeyChecking no" -i "./$PRIVATE_KEY_FILE" ubuntu@"$ip" << HERE
    set -x 
    sudo mkdir -p /opt/mysqlcluster/home
    cd /opt/mysqlcluster/home
    sudo wget -q http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz
    sudo tar xf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz
    sudo ln -s mysql-cluster-gpl-7.2.1-linux2.6-x86_64 mysqlc
    cd ~
    echo "export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc
    export PATH=/opt/mysqlcluster/home/mysqlc/bin:\$PATH" > mysqlc.sh
    sudo mv mysqlc.sh /etc/profile.d/mysqlc.sh
    source /etc/profile.d/mysqlc.sh
    sudo apt-get -qq update && sudo apt-get -qq install -y libncurses5
    sudo mkdir -p /opt/mysqlcluster/deploy/ndb_data
    sudo /opt/mysqlcluster/home/mysqlc/bin/ndbd -c "$MASTER_DNS"
HERE
done

# What is done here :
#    - Download and install the MYSQL to the standalone instance
#    - Download and source sakila database
#    - Create mysql user with all privileges
ssh -o "StrictHostKeyChecking no" -i "./$PRIVATE_KEY_FILE" ubuntu@"$STANDALONE_IP" << HERE
set -x 
sudo apt-get -qq update -y && sudo apt-get -qq install -y mysql-server
wget -q https://downloads.mysql.com/docs/sakila-db.tar.gz
tar -xzf sakila-db.tar.gz
sudo mysql -e "SOURCE /home/ubuntu/sakila-db/sakila-schema.sql;SOURCE /home/ubuntu/sakila-db/sakila-data.sql;USE sakila;SHOW FULL TABLES;"
sudo mysql -e "CREATE USER 'test'@'localhost' IDENTIFIED BY 'pass';GRANT ALL PRIVILEGES ON *.* TO 'test'@'localhost' WITH GRANT OPTION;
CREATE USER 'test'@'%' IDENTIFIED BY 'pass';GRANT ALL PRIVILEGES ON *.* TO 'test'@'%' WITH GRANT OPTION;"
HERE

# What is done here :
#    - Show connected cluster
#    - Start cluster 
ssh -o "StrictHostKeyChecking no" -i "./$PRIVATE_KEY_FILE" ubuntu@"$MASTER_IP" << HERE
set -x 
source /etc/profile.d/mysqlc.sh
sudo /opt/mysqlcluster/home/mysqlc/bin/ndb_mgm -e show
sudo /opt/mysqlcluster/home/mysqlc/bin/ndb_mgm -e 'all status'
sudo /opt/mysqlcluster/home/mysqlc/bin/mysqld --defaults-file=/opt/mysqlcluster/deploy/conf/my.cnf --user=root &
HERE

# What is done here :
#    - Download and source sakila database
#    - Create mysql user with all privileges
#    - Start node
ssh -o "StrictHostKeyChecking no" -i "./$PRIVATE_KEY_FILE" ubuntu@"$MASTER_IP" << HERE
set -x 
source /etc/profile.d/mysqlc.sh
wget -q https://downloads.mysql.com/docs/sakila-db.tar.gz
tar -xzf sakila-db.tar.gz
sudo /opt/mysqlcluster/home/mysqlc/bin/mysql -e "SOURCE /home/ubuntu/sakila-db/sakila-schema.sql;SOURCE /home/ubuntu/sakila-db/sakila-data.sql;USE sakila;SHOW FULL TABLES;"
sudo /opt/mysqlcluster/home/mysqlc/bin/mysql -e "CREATE USER 'test'@'localhost' IDENTIFIED BY 'pass';GRANT ALL PRIVILEGES ON *.* TO 'test'@'localhost' WITH GRANT OPTION;
CREATE USER 'test'@'%' IDENTIFIED BY 'pass';GRANT ALL PRIVILEGES ON *.* TO 'test'@'%' WITH GRANT OPTION;"
HERE

# What is done here :
#    - Clone my public repo that contains the proxy python script 
#    - Install the required libraries
#    - Create environment variables text file
#    - Ping all slave instances and store values in text file
ssh -o "StrictHostKeyChecking no" -i "./$PRIVATE_KEY_FILE" ubuntu@"$PROXY_IP" << HERE
set -x 
git clone https://github.com/Rad-Ali/Advanced-Cloud-Computing-Final-Project.git
sudo apt-get -qq update && sudo apt-get install -qq -y python3-pip
sudo pip install pymysql
sudo pip install sshtunnel
echo "STANDALONE_IP=$STANDALONE_IP
MASTER_IP=$MASTER_IP
SLAVE0_IP=$SLAVE0_IP
SLAVE1_IP=$SLAVE1_IP
SLAVE2_IP=$SLAVE2_IP
PROXY_IP=$PROXY_IP
MASTER_DNS=$MASTER_DNS
SLAVE0_DNS=$SLAVE0_DNS
SLAVE1_DNS=$SLAVE1_DNS
SLAVE2_DNS=$SLAVE2_DNS
PROXY_DNS=$PROXY_DNS" > Advanced-Cloud-Computing-Final-Project/env_variables.txt
ping $SLAVE0_IP -c 1 | tail -n1  > Advanced-Cloud-Computing-Final-Project/slave0.txt
ping $SLAVE1_IP -c 1 | tail -n1  > Advanced-Cloud-Computing-Final-Project/slave1.txt
ping $SLAVE2_IP -c 1 | tail -n1  > Advanced-Cloud-Computing-Final-Project/slave2.txt
HERE

#Copy the private key of all AWS instances to the proxy to allow sshtunnels
scp -i "./$PRIVATE_KEY_FILE" $PRIVATE_KEY_FILE ubuntu@$PROXY_IP:~/Advanced-Cloud-Computing-Final-Project
