#!/usr/bin/env bash

source env_variables.txt

ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$MASTER_IP" << HERE
set -x 
source /etc/profile.d/mysqlc.sh
sudo apt-get -qq install -y sysbench
sudo /opt/mysqlcluster/home/mysqlc/bin/mysql -e "create database dbtest;"
sysbench oltp_read_write --table-size=1000000 --mysql-db=dbtest --mysql-host="$MASTER_IP" --mysql-user="test" --mysql-password="pass" prepare
sysbench oltp_read_write --table-size=1000000 --mysql-host="$MASTER_IP" --num-threads=6 --max-time=60 --max-requests=0 --mysql-db=dbtest --mysql-user="test" --mysql-password="pass" run
HERE

ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$STANDALONE_IP" << HERE
set -x 
source /etc/profile.d/mysqlc.sh
sudo apt-get -qq install -y sysbench
sudo mysql -e "create database dbtest;"
sysbench oltp_read_write --table-size=1000000 --mysql-db=dbtest --mysql-user="test" --mysql-password="pass" prepare
sysbench oltp_read_write --table-size=1000000 --num-threads=6 --max-time=60 --max-requests=0 --mysql-db=dbtest --mysql-user="test" --mysql-password="pass" run
HERE