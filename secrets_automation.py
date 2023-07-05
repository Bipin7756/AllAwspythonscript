import yaml
import os
import base64

namespace = 'covin-sit'

def list_existing_secrets():
    existing_secret_names = []
    with open(f"/home/ec2-user/{namespace}/ingress/secrets.yaml", "r") as stream:
        docs = yaml.safe_load_all(stream)
        for doc in docs:
            existing_secret_names.extend(doc['data'].keys())
    return existing_secret_names


def list_existing_deployments():
    deployments = [deployment for deployment in os.listdir(f'/home/ec2-user/{namespace}/kubefile')
                   if deployment.endswith("ml") and "frontend" not in deployment]
    return deployments


existing_deployments_list = list_existing_deployments()


def create_new_env_var(env_name, env_value):
    secret_name = env_name.lower().replace("_", "-")
    base64_value = str(base64.b64encode(bytes(env_value, 'utf-8'))).replace("b'", "").replace("'", "")
    with open(f"/home/ec2-user/{namespace}/ingress/secrets.yaml", "r") as read_stream:
        existing_secrets_list = list(yaml.safe_load_all(read_stream))
        new_secret_doc = {
            'apiVersion': 'v1',
            'kind': 'Secret',
            'metadata': {'name': secret_name},
            'data': {secret_name: base64_value}
        }
        existing_secrets_list.append(new_secret_doc)
    with open(f"/home/ec2-user/{namespace}/ingress/secrets.yaml", "w") as write_stream:
        yaml.safe_dump_all(existing_secrets_list, write_stream, default_flow_style=False, sort_keys=False)
    try:
        os.system(f"~/bin/kubectl apply -f /home/ec2-user/{namespace}/ingress/secrets.yaml -n {namespace}")
        print(f"Secret Created for {env_name} with name {secret_name} and value {base64_value}")
    except Exception as e:
        print(e)


def restart_deployment(env_name):
    deployments_to_restart = []
    for deployment in existing_deployments_list:
        with open(f"/home/ec2-user/{namespace}/kubefile/{deployment}", "r") as read_stream:
            existing_deployment = list(yaml.safe_load_all(read_stream))
            try:
                env_container = existing_deployment[1]["spec"]["template"]["spec"]["containers"][0]
                env_variables = env_container.get("env", [])
                for env_variable in env_variables:
                    if env_variable["name"] == env_name:
                        print("Matched")
                        if "micro" in deployment:
                            deployments_to_restart.append(deployment.replace("micro-", "").split(".")[0])
                        else:
                            deployments_to_restart.append(deployment.split(".")[0])
            except Exception as e:
                print(e)
    if len(deployments_to_restart) > 0:
        deployments_to_restart.append("All")
    else:
        sys.exit(f"Env Variable {env_name} is not used in any deployment")
    restart_or_not = int(input("Willing to restart Services having these variables\n1. Yes\n2. No\n"))
    if restart_or_not == 2:
        deployments_to_restart.remove("All")
        sys.exit(f"Secrets Updated but will be reflected once you restart the services: {','.join(deployments_to_restart)}")
    else:
        for deployment in deployments_to_restart:
            print(f"{deployments_to_restart.index(deployment) + 1}. {deployment}")
        selected_deployment = input("Select Deployment to make secret changes reflected. Enter 'All' to restart every service listed above or enter comma-separated numbers to select multiple services:\n")
        for restarting_deployment in selected_deployment.split(","):
            if deployments_to_restart[int(restarting_deployment) - 1] == "All":
                for deployment in deployments_to_restart:
                    if deployment != "All":
                        os.system(f"~/bin/kubectl rollout restart deployment/{deployment} -n {namespace}")
            else:
                os.system(f"~/bin/kubectl rollout restart deployment/{deployments_to_restart[int(restarting_deployment) - 1]} -n {namespace}")


def updating_existing_env_var(env_name):
    secret_present = False
    secret_name = env_name.lower().replace("_", "-")
    with open(f"/home/ec2-user/{namespace}/ingress/secrets.yaml", "r") as read_stream:
        existing_secrets_list = list(yaml.safe_load_all(read_stream))
        for secret in existing_secrets_list:
            for key in secret['data'].keys():
                if secret_name == key:
                    env_value = input(f"Enter Value of Variable {env_name} to Update:\n")
                    base64_value = str(base64.b64encode(bytes(env_value, 'utf-8'))).replace("b'", "").replace("'", "")
                    secret['data'][secret_name] = base64_value
                    secret_present = True
    if not secret_present:
        sys.exit(f"Env variable not present with name: {env_name}")
    with open(f"/home/ec2-user/{namespace}/ingress/secrets.yaml", "w") as write_stream:
        yaml.safe_dump_all(existing_secrets_list, write_stream, default_flow_style=False, sort_keys=False)
    try:
        os.system(f"~/bin/kubectl apply -f /home/ec2-user/{namespace}/ingress/secrets.yaml -n {namespace}")
        print(f"Secret Updated for {env_name} with name {secret_name} and value {base64_value}")
        restart_deployment(env_name)
    except Exception as e:
        print(e)


def add_var_to_deployment(env_name, deployments_to_add):
    secret_name = env_name.lower().replace("_", "-")
    env_present = False
    deployments_to_restart = []
    try:
        for deployment in deployments_to_add:
            deployment = existing_deployments_list[int(deployment) - 1]
            deployments_to_restart.append(deployment)
            with open(f"/home/ec2-user/{namespace}/kubefile/{deployment}", "r") as read_stream:
                existing_deployment = list(yaml.safe_load_all(read_stream))
                new_env_variable = {
                    'name': env_name,
                    'valueFrom': {
                        'secretKeyRef': {
                            'name': secret_name,
                            'key': secret_name
                        }
                    }
                }
                try:
                    env_container = existing_deployment[1]["spec"]["template"]["spec"]["containers"][0]
                    env_variables = env_container.get("env", [])
                    for env_variable in env_variables:
                        if env_variable["name"] == env_name:
                            env_present = True
                            print(f"{env_name} env variable already present in {deployment.split('.')[0]}")
                    if not env_present:
                        env_variables.append(new_env_variable)
                        env_container["env"] = env_variables
                except Exception as e:
                    print(e)
            with open(f"/home/ec2-user/{namespace}/kubefile/{deployment}", "w") as write_stream:
                yaml.safe_dump_all(existing_deployment, write_stream, default_flow_style=False, sort_keys=False)
                print(f"{env_name} env variable added in {deployment.split('.')[0]}")
        deployments_to_restart.append("All")
        for deployment in deployments_to_restart:
            print(f"{deployments_to_restart.index(deployment) + 1}. {deployment}")
        selected_deployment = input("Select Deployment to make secret changes reflected. Enter 'All' to add to every service listed above, or enter comma-separated numbers to select multiple services:\n")
        for restarting_deployment in selected_deployment.split(","):
            if deployments_to_restart[int(restarting_deployment) - 1] == "All":
                for deployment in deployments_to_restart:
                    if deployment != "All":
                        try:
                            with open(f"/home/ec2-user/{namespace}/kubefile/{deployment}", "r") as read_stream:
                                existing_deployment = list(yaml.safe_load_all(read_stream))
                                deployment_name = existing_deployment[1]["metadata"]["name"]
                                image_name = str(os.popen(f"~/bin/kubectl get deployment {deployment_name} -n {namespace} -o=jsonpath='{{$.spec.template.spec.containers[:1].image}}'").read()).strip()
                                existing_deployment[1]["spec"]["template"]["spec"]["containers"][0]["image"] = image_name
                            with open(f"/home/ec2-user/{namespace}/kubefile/{deployment}", "w") as write_stream:
                                yaml.safe_dump_all(existing_deployment, write_stream, default_flow_style=False, sort_keys=False)
                            os.system(f"~/bin/kubectl apply -f /home/ec2-user/{namespace}/kubefile/{deployment} -n {namespace}")
                        except Exception as e:
                            print(e)
            else:
                try:
                    with open(f"/home/ec2-user/{namespace}/kubefile/{deployments_to_restart[int(restarting_deployment) - 1]}", "r") as read_stream:
                        existing_deployment = list(yaml.safe_load_all(read_stream))
                        deployment_name = existing_deployment[1]["metadata"]["name"]
                        image_name = str(os.popen(f"~/bin/kubectl get deployment {deployment_name} -n {namespace} -o=jsonpath='{{$.spec.template.spec.containers[:1].image}}'").read()).strip()
                        existing_deployment[1]["spec"]["template"]["spec"]["containers"][0]["image"] = image_name
                    with open(f"/home/ec2-user/{namespace}/kubefile/{deployments_to_restart[int(restarting_deployment) - 1]}", "w") as write_stream:
                        yaml.safe_dump_all(existing_deployment, write_stream, default_flow_style=False, sort_keys=False)
                    os.system(f"~/bin/kubectl apply -f /home/ec2-user/{namespace}/kubefile/{deployments_to_restart[int(restarting_deployment) - 1]} -n {namespace}")
                except Exception as e:
                    print(e)

    except Exception as e:
        print(e)


existing_secret_names = list_existing_secrets()

create_or_update = int(input("1. Create a New Environment Variable\n2. Update an existing Environment Variable\n"))

if create_or_update == 1:
    env_name = input("Enter Environment Variable Name:\n")
    secret_name = env_name.lower().replace("_", "-")
    if secret_name in existing_secret_names:
        sys.exit("Secret Already Present. You should use Update option to update the existing secret")
    else:
        env_value = input(f"Enter Value of Variable {env_name}:\n")
        create_new_env_var(env_name, env_value)

elif create_or_update == 2:
    env_name = input("Enter Environment Variable Name:\n")
    secret_name = env_name.lower().replace("_", "-")
    if secret_name not in existing_secret_names:
        sys.exit("Secret Not Present. You should use Create option to create a new secret")
    else:
        updating_existing_env_var(env_name)

else:
    sys.exit("Invalid option selected. Exiting...")
