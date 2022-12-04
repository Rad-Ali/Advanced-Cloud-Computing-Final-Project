import pymysql.cursors

masterIP = ""

# Read Master IP from environment variables file
with open("env_variables.txt", 'r') as file:
    masterIP = file.readlines()[1][10:].replace("\n","")

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
        sql = "SELECT * FROM actor WHERE actor_id <10"
        cursor.execute(sql)
        result = cursor.fetchall()
        print(result)