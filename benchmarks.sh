#!/usr/bin/env bash

source env_variables.txt

ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$MASTER_IP" << HERE
set -x 
source /etc/profile.d/mysqlc.sh
sudo apt-get -qq install -y sysbench
sysbench oltp_read_write --table-size=1000000 --mysql-db="sakila" --mysql-host="$MASTER_IP" --mysql-user="test" --mysql-password="pass" prepare
sysbench oltp_read_write --table-size=1000000 --mysql-host="$MASTER_IP" --num-threads=16 --max-time=10 --max-requests=0 --mysql-db="sakila" --mysql-user="test" --mysql-password="pass" run
HERE

ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$STANDALONE_IP" << HERE
set -x 
source /etc/profile.d/mysqlc.sh
sudo apt-get -qq install -y sysbench
sysbench oltp_read_write --table-size=1000000 --mysql-db="sakila" --mysql-user="test" --mysql-password="pass" prepare
sysbench oltp_read_write --table-size=1000000 --num-threads=16 --max-time=10 --max-requests=0 --mysql-db="sakila" --mysql-user="test" --mysql-password="pass" run
HERE