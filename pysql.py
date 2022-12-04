import pymysql.cursors
import argparse
import random
#import pyping


def create_connection(IP,bindAddress=None):
    """Create connection with MySQL database

    Args:
        IP (str): instance IP to connect to
        bindAddress (str) : IP address of bound slave node

    Returns:
        connection: connection to instance's database
    """
    connection = pymysql.connect(host=IP,
                             user='test',
                             password='pass',
                             database='sakila',
                             cursorclass=pymysql.cursors.DictCursor,
                             bind_address=bindAddress
                             )

    return connection


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

slaveList = [slave0IP, slave1IP, slave2IP]

# Connect to the database
connectionType = "r"

if connectionType == "r":
    if queryType == "SELECT":
        connection = create_connection(masterIP, slaveList[random.randrange(3)])

        # Test connection with sakila database with a select query
        with connection:
            with connection.cursor() as cursor:
                # Read a single record
                cursor.execute(sql)
                result = cursor.fetchall()
                print(result)
    elif queryType == "INSERT":
        connection = create_connection(masterIP)
        with connection:
            with connection.cursor() as cursor:
                # Read a single record
                cursor.execute(sql)
                result = cursor.fetchall()
                print(result)
            connection.commit()