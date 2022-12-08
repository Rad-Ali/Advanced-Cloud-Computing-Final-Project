#!/usr/bin/env bash

# Import all the necessary IP and DNS addresses
source ./env_variables.txt

#EXAMPLE OF QUERY : "SELECT * FROM actor WHERE actor_id <=10"

# What is done here :
#    - Enter python script directory
#    - Run query with 1 or 2 arguments
ssh -o "StrictHostKeyChecking no" -i "$PRIVATE_KEY_FILE" ubuntu@"$PROXY_IP" << HERE
cd Advanced-Cloud-Computing-Final-Project/
python3 pysql.py --query "$1" $2
HERE