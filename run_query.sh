#!/usr/bin/env bash

source ./env_variables.txt

#EXAMPLE OF QUERY : "SELECT * FROM actor WHERE actor_id <=10"

ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$PROXY_IP" << HERE
cd Advanced-Cloud-Computing-Final-Project/
python3 pysql.py --query "$1" $2
HERE