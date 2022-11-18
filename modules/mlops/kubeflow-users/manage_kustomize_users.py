import json
import os
import random
import sys
from typing import Any, Dict, List

import boto3
import yaml
from passlib.hash import bcrypt

client = boto3.client("secretsmanager")
project_name = os.getenv("AWS_CODESEEDER_NAME", "addf")
account_id = os.getenv("AWS_ACCOUNT_ID", "*")
abs_path = "."


def _proj(name: str) -> str:
    return f"{project_name.upper()}_{name}"


deployment_name = os.getenv(_proj("DEPLOYMENT_NAME"), "")
module_name = os.getenv(_proj("MODULE_NAME"), "")


# Sample Metadata Payoad:
# {
#   "KubeflowUsers": [
#     {
#       "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess",
#       "secret": "addf-dataservice-users-kubeflow-users-kf-dgraeber",
#       "roleArn": "arn:aws:iam::123456789012:role/addf-mlops-somerolearn"
#     }
#   ],
#   "EksClusterName": "addf-mlops-core-eks-cluster"
# }


def generate_profile(email: str, role_arn: str, username: str) -> None:
    with open(f"{abs_path}/profiles/profile.template", "r") as file:
        profile = yaml.safe_load(file)
    profile["metadata"]["name"] = username
    profile["metadata"]["namespace"] = username
    profile["spec"]["owner"]["name"] = email
    if role_arn:
        plugins = []
        plugins.append({"kind": "AwsIamForServiceAccount", "spec": {"awsIamRole": role_arn}})
        profile["spec"]["plugins"] = plugins

    with open(f"{abs_path}/profiles/{username}-profile.yaml", "w") as file:
        yaml.dump(profile, file)


def generate_kustomize_config(info: List[Dict[str, str]]) -> None:
    with open(f"{abs_path}/kustomize/config.template", "r") as file:
        config_map = yaml.safe_load(file)
    config_map["staticPasswords"] = info
    with open(f"{abs_path}/kustomize/config.yaml", "w") as file:
        yaml.dump(config_map, file)
    print("Kustomize config written")


def create(users: Dict[str, Any]):
    kustomize_map = []
    user_metadata = {}
    for user in users["KubeflowUsers"]:
        try:
            client.describe_secret(SecretId=user["secret"])
            secret_json = json.loads(client.get_secret_value(SecretId=user["secret"])["SecretString"])
            encoded_pwd = bcrypt.using(rounds=12, ident="2y").hash(secret_json["password"])
            username = secret_json["username"]
            email = secret_json["email"]
            rolearn = user["roleArn"]
            generate_profile(email=email, role_arn=rolearn, username=username)
            kustomize_map.append(
                {
                    "email": email,
                    "hash": encoded_pwd,
                    "username": username,
                    "userID": str(random.randint(10000, 900000)),
                }
            )

            user_metadata[secret_json["username"]] = user
        except Exception as e:
            print(e)
            print(f"Some error with the secret {user['secret']} - skipping")
            continue
    generate_kustomize_config(kustomize_map)


if __name__ == "__main__":
    users_str = sys.argv[1]
    create(json.loads(users_str))
