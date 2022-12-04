import pymysql.cursors
import argparse

#Parse query arguments
parser = argparse.ArgumentParser(description='Instance setup.')
parser.add_argument('--query', help='Run query')
args = parser.parse_args()

#Verify what type of operation is being requested 
sql = ""
queryType = ""
if args.query is None:
    sql = "SELECT * FROM actor WHERE actor_id <=1"
    queryType= "SELECT"
else:
    sql = args.query
    if sql.upper().startswith("SELECT") > -1: 
        queryType= "SELECT"
    elif sql.upper().startswith("INSERT") > -1: 
        queryType= "INSERT"

masterIP = ""
slave0IP = ""
slave1IP = ""
slave2IP = ""

# Read IPs from environment variables file
with open("env_variables.txt", 'r') as file:
    lines = file.readlines()
    masterIP = lines[1][10:].replace("\n","")
    slave0IP = lines[2][10:].replace("\n","")
    slave1IP = lines[3][10:].replace("\n","")
    slave2IP = lines[4][10:].replace("\n","")

# Connect to the database
connection = pymysql.connect(host=masterIP,
                             user='test',
                             password='pass',
                             database='sakila',
                             cursorclass=pymysql.cursors.DictCursor)

# Test connection with sakila database with a select query
with connection:
    with connection.cursor() as cursor:
        # Read a single record
        cursor.execute(sql)
        result = cursor.fetchall()
        print(result)