import pymysql.cursors
import argparse
import random
from sshtunnel import open_tunnel

def create_connection(IP):
    """Create connection with MySQL database

    Args:
        IP (str): instance IP to connect to

    Returns:
        connection: connection to instance's database
    """
    connection = pymysql.connect(host=IP,
                             user='test',
                             password='pass',
                             database='sakila',
                             cursorclass=pymysql.cursors.DictCursor
                             )

    return connection

def execute_sql(connection, sql):
    """Execute the sql query

    Args:
        connection: connection to the SQL database
        sql (str) : SQL query string
    Returns:
        result: result of sql query
    """
    with connection:
            with connection.cursor() as cursor:
                # Read a single record
                cursor.execute(sql)
                result = cursor.fetchall()
                return result

def open_bound_tunnel(bindAddress, sql):
    """Opens ssh tunnel to the required slave and executes the sql query

    Args:
        bindAddress (str) : IP address of the slave
        sql (str) : SQL query string
    Returns:
        result: result of sql query
        connection : connection to the database
    """
    with open_tunnel(
    (bindAddress, 22),
    ssh_username="ubuntu",
    ssh_pkey="private_key_LAB3_KEY.pem",
    remote_bind_address=(masterIP, 3306)
    ) as server:
        connection = create_connection(masterIP)
        return execute_sql(connection, sql), connection

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
query = ""
queryType = ""
if args.query is None:
    query = "SELECT * FROM actor WHERE actor_id <=1"
    queryType= "SELECT"
else:
    query = args.query
    if query.upper().startswith("SELECT") > -1: 
        queryType= "SELECT"
    elif query.upper().startswith("INSERT") > -1: 
        queryType= "INSERT"

masterIP = ""
slave0IP = ""
slave1IP = ""
slave2IP = ""

# Read IPs from environment variables file
with open("env_variables.txt", 'r') as file:
    lines = file.readlines()
    masterIP = lines[1][lines[1].find('=')+1:].replace("\n","")
    slave0IP = lines[2][lines[2].find('=')+1:].replace("\n","")
    slave1IP = lines[3][lines[3].find('=')+1:].replace("\n","")
    slave2IP = lines[4][lines[4].find('=')+1:].replace("\n","")

slaveList = [slave0IP, slave1IP, slave2IP]

# Connect to the database with respect to query type
if queryType == "SELECT":
    # Execute SQL SELECT query depending on type of implementation                                      
    if args.random:                                                 # Random
        print(open_bound_tunnel(slaveList[random.randrange(3)], query))
    elif args.customized :                                          # Customized
        slave0Time = read_ping("slave0.txt")
        slave1Time = read_ping("slave1.txt")
        slave2Time = read_ping("slave2.txt")
        boundAddress = slave0IP
        if slave1Time <  slave0Time: boundAddress = slave1IP
        if slave2Time < slave1Time or slave2Time < slave0Time: boundAddress = slave2IP
        print(open_bound_tunnel(boundAddress, query))
    else :                                                          # Direct hit
        connection = create_connection(masterIP)
        print(execute_sql(connection, query))
    # Connect to the database with respect to query type
elif queryType == "INSERT":
    # Execute SQL INSERT query depending on type of implementation                                      
    if args.random:                                                 # Random
        result, con = open_bound_tunnel(slaveList[random.randrange(3)], query)  
        print(result)
        con.commit()      
    elif args.customized :                                          # Customized
        slave0Time = read_ping("slave0.txt")
        slave1Time = read_ping("slave1.txt")
        slave2Time = read_ping("slave2.txt")
        boundAddress = slave0IP
        if slave1Time <  slave0Time: boundAddress = slave1IP
        if slave2Time < slave1Time or slave2Time < slave0Time: boundAddress = slave2IP
        result, con = open_bound_tunnel(boundAddress, query)
        print(result)
        con.commit()
    else :                                                          # Direct hit
        con = create_connection(masterIP)
        print(execute_sql(con, query))
        con.commit()
    
