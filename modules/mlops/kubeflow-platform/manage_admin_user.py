import json
import os
import sys

import boto3  # type: ignore

client = boto3.client("iam")

ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "*")

policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["iam:Create*", "iam:Delete*", "iam:List*", "iam:Attach*", "iam:Detach*"],
            "Resource": [
                f"arn:aws:iam::{ACCOUNT_ID}:role/kf-ack-sm-controller*",
                f"arn:aws:iam::{ACCOUNT_ID}:policy/sm-studio-full-access*",
            ],
        }
    ],
}


def role_name_from_arn(role_arn: str) -> str:
    return role_arn.split("/")[1]


def fetch_policy_arn(policy_name: str) -> str:
    policy_arn = f"arn:aws:iam::{ACCOUNT_ID}:policy/{policy_name}"
    try:
        p = client.get_policy(PolicyArn=policy_arn)["Policy"]["Arn"]
        print(f"Found Policy Arn {p}")
    except Exception:
        p = create_policy(policy_name)
        print(f"Created Policy Arn {p}")
    return p


def create_policy(policy_name: str) -> str:
    resp = client.create_policy(PolicyName=policy_name, PolicyDocument=json.dumps(policy))
    return resp["Policy"]["Arn"]


def attach_role_policy(policy_name: str, role_arn: str):
    role_name = role_name_from_arn(role_arn)
    policies_attached = client.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]

    policies = [p["PolicyName"] for p in policies_attached]

    client.attach_role_policy(
        RoleName=role_name, PolicyArn=fetch_policy_arn(policy_name)
    ) if policy_name not in policies else print(f"{policy_name} already attached to {role_arn} ")


def detach_role_policy(policy_name: str, role_arn: str):
    role_name = role_name_from_arn(role_arn)
    policies = client.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]

    for p in policies:
        client.detach_role_policy(RoleName=role_name, PolicyArn=p["PolicyArn"]) if p["PolicyName"] in [
            policy_name
        ] else None

    try:
        client.delete_policy(PolicyArn=f"arn:aws:iam::{ACCOUNT_ID}:policy/{policy_name}")
    except Exception:
        print("Had an error deleting....moving along")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("You must pass in 'create' or 'delete', the name of the policy, and the arn of the role")
    elif sys.argv[1] == "create":
        attach_role_policy(policy_name=sys.argv[2], role_arn=sys.argv[3])
    elif sys.argv[1] == "delete":
        detach_role_policy(policy_name=sys.argv[2], role_arn=sys.argv[3])
