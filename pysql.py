import pymysql.cursors
import argparse
import random


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
                             #bind_address=bindAddress
                             )

    return connection

def read_ping(filename):
    """Read the ping value of slave from textfile

    Args:
        filename (str): filename of slave textfile

    Returns:
        (float): ping time value
    """
    with open(filename, 'r') as file:
        line=file.readline()
        temp = line[line.find('=')+2:]
        temp = temp[:temp.find('/')]
        print(temp)
        return float(temp)
        


#Parse query arguments
parser = argparse.ArgumentParser(description='Instance setup.')
parser.add_argument('--query', help='Run query')
group = parser.add_mutually_exclusive_group()
group.add_argument('-r', '--random', action='store_true', default=False)
group.add_argument('-c', '--customized', action='store_true', default=False)
args = parser.parse_args()
print(args)
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

bindAddress = None                                           # Direct hit
if args.random: bindAddress = slaveList[random.randrange(3)] # Random
if args.customized :                                         # Customized
    slave0Time = read_ping("slave0.txt")
    slave1Time = read_ping("slave1.txt")
    slave2Time = read_ping("slave2.txt")
    bindAddress = slave0IP
    if slave1Time <  slave0IP: bindAddress = slave1IP
    if slave2Time < slave1Time or slave2Time < slave0Time: bindAddress = slave2IP

print(bindAddress)

# Connect to the database with respect to query type
if queryType == "SELECT":
    connection = create_connection(masterIP)

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