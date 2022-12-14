import boto3
from botocore.exceptions import ClientError
from os import path
import argparse

parser = argparse.ArgumentParser(description='Instance setup.')
parser.add_argument('--kill', action='store_true', default=False, help='Kill all running instances and exit')
args = parser.parse_args()

EC2_RESOURCE = boto3.resource('ec2')
EC2_CLIENT = boto3.client('ec2')

NUM_SLAVES = 3

def create_ec2(instance_type, sg_id, key_name, instance_name):
    """Creates an EC2 instance

    Args:
        instance_type (str): Instance type (t2.micro, ...)
        sg_id (str): Security group ID
        key_name (str): SSH key name
        instrance_name (str) : instance name
    Returns:
        instance: The created instance object
    """
    instance = EC2_RESOURCE.create_instances(
        ImageId='ami-0149b2da6ceec4bb0',
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        Monitoring={'Enabled': True},
        SecurityGroupIds=[sg_id],
        KeyName=key_name,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': instance_name
                    },
                ]
            },
        ]
    )[0]
    print(f'{instance} is starting')
    return instance


def create_security_group():
    """Creates a security group for the lab 3 needs

    Returns:
        security_group_id: The created security group ID
    """
    sec_group_name = 'lab3-security-group'
    security_group_id = None
    try:
        response = EC2_CLIENT.create_security_group(
            GroupName=sec_group_name,
            Description='Security group for the ec2 instances used in Lab3'
        )
        security_group_id = response['GroupId']
        print(f'Successfully created security group {security_group_id}')
        sec_group_rules = [
            {'IpProtocol': '-1',
             'FromPort': 0,
             'ToPort': 65535,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
        data = EC2_CLIENT.authorize_security_group_ingress(GroupId=security_group_id,
                                                           IpPermissions=sec_group_rules)
        print(f'Successfully updated security group rules with : {sec_group_rules}')
        return security_group_id
    except ClientError as e:
        try:  # if security group exists already, find the security group id
            response = EC2_CLIENT.describe_security_groups(
                Filters=[
                    dict(Name='group-name', Values=[sec_group_name])
                ])
            security_group_id = response['SecurityGroups'][0]['GroupId']
            print(f'Security group already exists with id {security_group_id}.')
            return security_group_id
        except ClientError as e:
            print(e)
            exit(1)


def create_private_key_filename(key_name):
    """Generates a filename to save the key pair

    Args:
        key_name (str): key name

    Returns:
        str: Private key filename
    """
    return f'private_key_{key_name}.pem'


def create_key_pair(key_name, private_key_filename):
    """Generates a key pair to access our instance

    Args:
        key_name (str): key name
        private_key_filename (str): filename to save the private key to
    """
    response = EC2_CLIENT.describe_key_pairs()
    kp = [kp for kp in response['KeyPairs'] if kp['KeyName'] == key_name]
    if len(kp) > 0 and not path.exists(private_key_filename):
        print(f'{key_name} already exists distantly, but the private key file has not been downloaded. Either delete the remote key or download the associate private key as {private_key_filename}.')
        exit(1)

    print(f'Creating {private_key_filename}')
    if path.exists(private_key_filename):
        print(f'Private key {private_key_filename} already exists, using this file.')
        return

    response = EC2_CLIENT.create_key_pair(KeyName=key_name)
    with open(private_key_filename, 'w+') as f:
        f.write(response['KeyMaterial'])
    print(f'{private_key_filename} written.')


def retrieve_public_ip(instance_ids):
    """Retrieves an instance's public IP

    Args:
        instance_id (str): instance id

    Returns:
        str: Instance's public IP
    """
    print(f'Retrieving instance {instance_ids} public IP...')

    instance_ips = []
    for id in instance_ids:
        instance_config = EC2_CLIENT.describe_instances(InstanceIds=[id])
        instance_ips.append(instance_config["Reservations"][0]['Instances'][0]['PublicIpAddress'])
    return instance_ips

def retrieve_private_dns(instance_ids):
    """Retrieves instances' private DNS

    Args:
        instance_id (str): instance id

    Returns:
        str: Instance's private DNS
    """
    instance_dns = []
    for id in instance_ids:
        instance_config = EC2_CLIENT.describe_instances(InstanceIds=[id])
        instance_dns.append(instance_config["Reservations"][0]['Instances'][0]['PrivateDnsName'])
    return instance_dns

def start_instance():
    """Starts master and slave instances, with the lab3 configuration.
    """
    # Create the standalone instance with the key pair
    standalone = create_ec2('t2.micro', sg_id, key_name, "standalone")

    # Create the master instance with the key pair
    master = create_ec2('t2.micro', sg_id, key_name, "master")

    # Create the slave instances with the key pair
    slave = []
    for i in range(NUM_SLAVES):
        slave.append(create_ec2('t2.micro', sg_id, key_name, "slave "+str(i)))

    proxy = create_ec2('t2.large', sg_id, key_name, "proxy")

    print(f'Waiting for standalone {standalone.id} to be running...')
    standalone.wait_until_running()

    print(f'Waiting for master {master.id} to be running...')
    master.wait_until_running()

    for i in range(NUM_SLAVES):
        print(f'Waiting for slave {i} {slave[i].id} to be running...')
        slave[i].wait_until_running()

    print(f'Waiting for proxy {proxy.id} to be running...')
    proxy.wait_until_running()

    # Get the instance's IP
    instance_ips = retrieve_public_ip([standalone.id, master.id, slave[0].id, slave[1].id, slave[2].id, proxy.id])
    intances_dns = retrieve_private_dns([master.id, slave[0].id, slave[1].id, slave[2].id, proxy.id])

    with open('env_variables.txt', 'w+') as f:
        f.write(f'STANDALONE_IP={instance_ips[0]}\n')
        f.write(f'MASTER_IP={instance_ips[1]}\n')
        f.write(f'SLAVE0_IP={instance_ips[2]}\n')
        f.write(f'SLAVE1_IP={instance_ips[3]}\n')
        f.write(f'SLAVE2_IP={instance_ips[4]}\n')
        f.write(f'PROXY_IP={instance_ips[5]}\n')
        f.write(f'MASTER_DNS={intances_dns[0]}\n')
        f.write(f'SLAVE0_DNS={intances_dns[1]}\n')
        f.write(f'SLAVE1_DNS={intances_dns[2]}\n')
        f.write(f'SLAVE2_DNS={intances_dns[3]}\n')
        f.write(f'PROXY_DNS={intances_dns[4]}\n')
        f.write(f'PRIVATE_KEY_FILE={private_key_filename}\n')
    print('Wrote instance\'s IP and private key filename to env_variables.txt')
    print(f'Standalone {standalone.id} started. Access it with \'ssh -i {private_key_filename} ubuntu@{instance_ips[0]}\'')
    print(f'Master {master.id} started. Access it with \'ssh -i {private_key_filename} ubuntu@{instance_ips[1]}\'')
    for i in range(NUM_SLAVES):
        print(f'Slave {i} - {master.id} started. Access it with \'ssh -i {private_key_filename} ubuntu@{instance_ips[i+2]}\'')
    print(f'Proxy {proxy.id} started. Access it with \'ssh -i {private_key_filename} ubuntu@{instance_ips[5]}\'')
    


def terminate_all_running_instances():
    """Terminate all currently running instances.
    """
    response = EC2_CLIENT.describe_instances()
    instance_ids = [instance['Instances'][0]['InstanceId'] for instance in response['Reservations']
        if instance['Instances'][0]['State']['Name'] == 'running']
    print(f'Terminating : {instance_ids}')
    try:
        EC2_CLIENT.terminate_instances(InstanceIds=[instance_id for instance_id in instance_ids])
    except ClientError as e:
        print('Failed to terminate the instances.')
        print(e)


if __name__ == "__main__":
    if args.kill:
        terminate_all_running_instances()
        exit(0)

    # Create a key pair
    key_name = 'LAB3_KEY'
    private_key_filename = create_private_key_filename(key_name)
    create_key_pair(key_name, private_key_filename)

    # Create a security group
    sg_id = create_security_group()
    start_instance()

