import pymysql
import csv
import os
import boto3

s3_client = boto3.client('s3')

table_names = ['m_district']
#table_names = ['tbl_map_material_frequency']
file_names = ['m_district.csv']
#file_names=['tbl_map_material_frequency.csv']

s3_bucket='cowin-redshift-test'
db_user = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-sit | grep user | head -n 1 | awk {'print $1}') env -n covin-sit | grep AUDIT_USER | awk -F = '{ print $2 }'").read()).strip()
db_password = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-sit | grep user | head -n 1 | awk {'print $1}') env -n covin-sit | grep COVID_AUDIT_PASSWORD | awk -F = '{ print $2 }'").read()).strip()
db_name = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-sit | grep user | head -n 1 | awk {'print $1}') env -n covin-sit | grep COVID_DATABASE | awk -F = '{ print $2 }'").read()).strip()
db_host="covid-sit-new-cluster.cluster-ro-ctqwkgbpzdlv.ap-south-1.rds.amazonaws.com"
con = pymysql.connect(user=db_user, passwd=db_password, host=db_host, db=db_name)
cursor = con.cursor()

for table in table_names:
    query = "SELECT * FROM %s;" % table
    try:
        cursor.execute(query)
        print(table)
        with open('/home/ec2-user/cowin-rds2redshift/table_dumps/%s.csv' % table ,'w') as f:
            writer = csv.writer(f, delimiter="|")
            for row in cursor.fetchall():
                writer.writerow(row)
    except Exception as e:
        print(e)

for table in file_names:
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file('/home/ec2-user/cowin-rds2redshift/table_dumps/%s' % table, s3_bucket, table)
    except Exception as e:
        print(e)

#os.system('rm /home/e:c2-user/mysql_backup/table_dumps/*.csv')
