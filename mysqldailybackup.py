import time
import datetime
import pipes
import os
import boto3

s3_client = boto3.client('s3')

stack = "SIT"

TIMESTAMP = time.strftime('%d%m%Y%H%M')


def cowin_sql_backup():
    s3_bucket = "cowin-redshift-test"
    backup_file_name = "covid-" + stack + "-" + TIMESTAMP + ".sql"
    db_user = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-sit | grep user | head -n 1 | awk {'print $1}') env -n covin-sit | grep AUDIT_USER | awk -F = '{ print $2 }'").read()).strip()
    db_password = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-sit | grep user | head -n 1 | awk {'print $1}') env -n covin-sit | grep AUDIT_PASSWORD | awk -F = '{ print $2 }'").read()).strip()
    db_names = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-sit | grep user | head -n 1 | awk {'print $1}') env -n covin-sit | grep AUDIT_DATABASE | awk -F = '{ print $2 }'").read()).strip()
    db_name = (db_names.split())[0]
    db_host = "covid-sit-new.ctqwkgbpzdlv.ap-south-1.rds.amazonaws.com"
    db_dump_cmd = "mysqldump --ignore-table=" + db_name + ".user_audit --ignore-table=" + db_name + ".user_notifications --ignore-table=" + db_name + ".import_audit --single-transaction -h " + db_host + " -u " + db_user + " -p" + db_password + " " + db_name + " > " + backup_file_name
    print("Dump is creating for covid")
    os.system(db_dump_cmd)
    create_tar_cmd = "tar -zcvf " + backup_file_name + ".tar.gz " +  backup_file_name
    os.system(create_tar_cmd)
    tar_file_name = backup_file_name + ".tar.gz"
    s3_file_path = stack + "/" + time.strftime('%Y') + "/" + time.strftime('%m') + "/" + tar_file_name
    response = s3_client.upload_file(tar_file_name, s3_bucket, s3_file_path)
    os.system("rm -rf " + backup_file_name + "*")
    return response

def uip_sql_backup():
    s3_bucket = "cowin-redshift-test"
    backup_file_name = "uip-" + stack + "-" + TIMESTAMP + ".sql"
    db_user = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-sit | grep user | head -n 1 | awk {'print $1}') env -n covin-sit | grep AUDIT_USER | awk -F = '{ print $2 }'").read()).strip()
    db_password = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-sit | grep user | head -n 1 | awk {'print $1}') env -n covin-sit | grep AUDIT_PASSWORD | awk -F = '{ print $2 }'").read()).strip()
    db_names = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-sit | grep user | head -n 1 | awk {'print $1}') env -n covin-sit | grep AUDIT_DATABASE | awk -F = '{ print $2 }'").read()).strip()
    db_name = (db_names.split())[1]
    db_host = "covid-sit-new.ctqwkgbpzdlv.ap-south-1.rds.amazonaws.com"
    db_dump_cmd = "mysqldump --ignore-table=" + db_name + ".user_audit --ignore-table=" + db_name + ".user_notifications --ignore-table=" + db_name + ".import_audit --single-transaction -h " + db_host + " -u " + db_user + " -p" + db_password + " " + db_name + " > " + backup_file_name
    print("Dump is creating for uip")
    os.system(db_dump_cmd)
    create_tar_cmd = "tar -zcvf " + backup_file_name + ".tar.gz " +  backup_file_name
    os.system(create_tar_cmd)
    tar_file_name = backup_file_name + ".tar.gz"
    s3_file_path = stack + "/" + time.strftime('%Y') + "/" + time.strftime('%m') + "/" + tar_file_name
    response = s3_client.upload_file(tar_file_name, s3_bucket, s3_file_path)
    os.system("rm -rf " + backup_file_name + "*")
    return response

cowin_backup = cowin_sql_backup()
uip_backup = uip_sql_backup()
