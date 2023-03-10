try:
    import ast
    import os
    from botocore.exceptions import ClientError, NoCredentialsError
    import boto3
    from dynamodb_json import json_util as json
except Exception as e:
    print(e)

REGION_NAME = "ap-south-1"
client = boto3.client('dynamodb', region_name=REGION_NAME)
s3 = boto3.client('s3') 

env = 'SIT'
bucket = "cowin-redshift-test"
s3_prefix = "dynamodb2redshift/{}/".format(env)
TABLE_LIST = [
        'beneficiary_registration_sit',
        'beneficiary_grievance_sit',
        'beneficiary_tracker_sit',
        'session_allocation_sit',
        'session_allocation_uip_sit',
        'uip_appointment_sit',
        'uip_beneficiary_registration_sit',
        'uip_tracker_sit',
        'uip_vaccination_sit'
]

main_path = os.getcwd()

def scan_db(client,table):
    scan_kwargs = {"TableName":table}
    complete = False
    records = []
    while not complete:
        try:
            response = client.scan(**scan_kwargs)
        except ClientError as error:
            raise Exception('Error quering DB: {}'.format(error))
        records.extend(response.get('Items', []))
        next_key = response.get('LastEvaluatedKey')
        scan_kwargs['ExclusiveStartKey'] = next_key
        complete = True if next_key is None else False
    return records

def upload_to_aws(s3,file_name, bucketName):
    try:
        s3.upload_file(main_path + "/" + file_name, bucketName, s3_prefix + file_name)
        print(file_name + " Upload Successful")
        return True
    except FileNotFoundError:
        print(file_name + " The file was not found")
        return False
    except NoCredentialsError:
        print(file_name + " Credentials not available")
        return False

for table in TABLE_LIST:
    data = scan_db(client,table)
    output = json.loads(data)

    print("Exporting table {} to csv".format(table))
    with open(main_path + "/{}.json".format(table),"w") as outputfile:
        for i in output:
            outputfile.write(str(i).replace("'",'"').replace("True","true").replace("False","false")+'\n')
    upload_to_aws(s3,"{}.json".format(table),bucket)
    os.remove(main_path + "/{}.json".format(table))
