#!/usr/bin/env python3


import argparse
import json
from typing import Dict, cast

import boto3

client = boto3.client("secretsmanager")


def get_payload(email: str, pwd: str, username: str) -> str:
    return json.dumps({"email": email, "password": pwd, "username": username})


def create_pwd() -> str:
    return cast(
        str,
        client.get_random_password(
            PasswordLength=6,
            ExcludeNumbers=False,
            ExcludePunctuation=True,
            ExcludeUppercase=False,
            ExcludeLowercase=False,
            IncludeSpace=False,
        )["RandomPassword"],
    )


def create(payload: Dict[str, str], secretname: str) -> Dict[str, str]:
    if not payload.get("password"):
        payload["password"] = create_pwd()
    try:
        response = client.create_secret(Name=secretname, SecretString=json.dumps(payload))
        return {"ARN": response["ARN"], "secretname": response["Name"]}

    except Exception as e:
        print(e)
        print(f"The AWS SecretManager name {secretname} already exists")
        return {}


parser = argparse.ArgumentParser()

parser.add_argument("--username", "-u", help="The username for the user")
parser.add_argument("--email", "-e", help="The email for the user - will alos be the login")
parser.add_argument("--secretname", "-s", help="The name of the AWS SecretManager storing this info")
parser.add_argument(
    "--password", "-p", help="The password for the user -- **** OPTIONAL - we will generate one if not provided"
)
args = parser.parse_args()
if None in [args.username, args.email, args.secretname]:
    print("You MUST provide a secretname, username and email address - MUST!!!!  Try running --help for help")
    exit(1)

print("--> We have all the info we need...creating AWS Secret for Kubeflow User Support!!")

if None in [args.password]:
    print("  --> We will also create a custom password for you.")


payload = {"username": args.username, "email": args.email, "password": args.password}

re = create(payload, args.secretname)
print(json.dumps(re))
print("To get the info, just call :")
print(
    f"aws secretsmanager get-secret-value \
--secret-id {re['secretname']} \
--query SecretString \
--output text \
| jq -r"
)
