import boto3
import pymysql
import os
import requests

api_gateway_client = boto3.client('apigateway',region_name='ap-south-1')
waf_client = boto3.client('wafv2',region_name='us-east-1')
rest_api_id = '7wfe5i1mu8'
stage_name = ''
usage_plan_id = ''
script = True


def createAPIGatewayKey(client, rest_api_id):
    print('1. PROD\n2. SIT\n')
    stage_number = int(input("Enter Environment to create API Key\n"))
    partner_name = input("Enter Partner Name\n")
    if stage_number == 1:
        stage_name = 'prod'
        usage_plan_id = '344x78'
    else:
        stage_name = 'sit'
        usage_plan_id = '2wdb34'
    name_of_key = partner_name + ' ' + stage_name.upper() 
    description = ''
    try:
        api_key_response = client.create_api_key(
            name=name_of_key,
            description=description,
            enabled=True,
            generateDistinctId=False,
            stageKeys=[
                 {
                    'restApiId': rest_api_id,
                    'stageName': stage_name
                },
            ]
        )
        api_key_id = api_key_response['id']
        api_key_value = api_key_response['value']

        try:
            plan_response = client.create_usage_plan_key(
                usagePlanId=usage_plan_id,
                keyId=api_key_id,
                keyType='API_KEY')

            insertIntoSql(api_key_value, name_of_key)
            refreshKeysRequest(api_key_value)

        except Exception as e:
            print('Attaching Usage Plan Error {}'.format(e))



    except Exception as e:
        print('Create API Key Error {}'.format(e))
    
 
def insertIntoSql(api_key_value, name_of_key):
    db_user = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-prod | grep user | head -n 1 | awk {'print $1}') env -n covin-prod | grep AUDIT_USER | awk -F = '{ print $2 }'").read()).strip()
    db_password = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-prod | grep user | head -n 1 | awk {'print $1}') env -n covin-prod | grep AUDIT_PASSWORD | awk -F = '{ print $2 }'").read()).strip()
    db_name = str(os.popen("~/bin/kubectl exec -it $(~/bin/kubectl get pods -n covin-prod | grep user | head -n 1 | awk {'print $1}') env -n covin-prod | grep AUDIT_DATABASE | awk -F = '{ print $2 }'").read()).strip()
    db_host="covid-prod.cluster-ctqwkgbpzdlv.ap-south-1.rds.amazonaws.com"
    
    con = pymysql.connect(user=db_user, passwd=db_password, host=db_host, db=db_name)
    cursor = con.cursor()

    query = "INSERT INTO m_partner_api_keys VALUES('{}', '{}', '{}')".format(api_key_value, name_of_key.lower().replace(' ',''), name_of_key)
    cursor.execute(query)
    con.commit()

    print("API Key : {}".format(api_key_value))
    print("Name of Key : {}".format(name_of_key))


def refreshKeysRequest(api_key_value):
    Headers = { "x-api-key": api_key_value }
    response = requests.get("https://api.cowin.gov.in/api/v2/auth/refreshPartnerKeys", headers=Headers)
    print("Above API Key Created Successfully")


def whitelistPartnerIP(waf_client):
    ip_whitelist_decision = input("Need to Whitelist an IP for Partner? Y for [Yes], N for [No]\n")
    if ip_whitelist_decision.lower() == "y":
        ips_to_whitelist = input("Enter IP to whitelist, if multiple ips then enter with comma separated way\n")
        ips_to_whitelist.replace(" ","")
        ips_to_whitelist_array = ips_to_whitelist.split(",")
        print("IPs to be whitelisted for Partners\n")
        for i in ips_to_whitelist_array:
            print("{}\n".format(i))
        ips_whitelist_confirm = input("Enter Y to Confirm, N to Reject\n")
        if ips_whitelist_confirm.lower() == "y":
            addIpIntoWAFIpSet(waf_client, ips_to_whitelist_array)
        else:
            print("")
    else:
        print("")


def addIpIntoWAFIpSet(waf_client, ips_to_whitelist_array):
    partners_waf_ip_set_v4 = '82b6f3c4-a9bf-4f03-85a2-7ba4a82d01fd'
    partners_waf_ip_set_v6 = '1141630f-ebf0-40ac-b71c-8078540f61b6'
    for ip in ips_to_whitelist_array:
        if len(ip) < 20:
            ip_get_response = waf_client.get_ip_set(
                Name='WhitelistedPartners',
                Scope='CLOUDFRONT',
                Id=partners_waf_ip_set_v4
            )
            lock_token = ip_get_response['LockToken']
            ip_v4_addresses = ip_get_response['IPSet']['Addresses']
            ip_v4_addresses.append(str(ip))

            ip_set_response = waf_client.update_ip_set(
                Name='WhitelistedPartners',
                Scope='CLOUDFRONT',
                Id=partners_waf_ip_set_v4,
                Addresses=ip_v4_addresses,
                LockToken=lock_token
            )  
            print("IPv4 {} whitelisted".format(ip))
        else:
            ip_get_response = waf_client.get_ip_set(
                Name='WhitelistedIPV6Partners',
                Scope='CLOUDFRONT',
                Id=partners_waf_ip_set_v6
            )
            lock_token = ip_get_response['LockToken']
            ip_v6_addresses = ip_get_response['IPSet']['Addresses']
            ip_v6_addresses.append(str(ip))
            ip_set_response = waf_client.update_ip_set(
                Name='WhitelistedIPV6Partners',
                Scope='CLOUDFRONT',
                Id=partners_waf_ip_set_v6,
                Addresses=ip_v6_addresses,
                LockToken=ip_get_response['LockToken']
            )
            print("IPv6 {} whitelisted".format(ip))

print("Available Options\n1. Create API Key\n2. Whitelist IP\n3. Both\n")
option = input("Enter Your Option\n")

if int(option) == 1 and script:
    createAPIGatewayKey(api_gateway_client, rest_api_id)
elif int(option) == 2 and script:
    whitelistPartnerIP(waf_client)
elif script:
    createAPIGatewayKey(api_gateway_client, rest_api_id)
    whitelistPartnerIP(waf_client)







