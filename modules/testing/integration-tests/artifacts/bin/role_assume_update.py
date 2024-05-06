import json
import sys

import boto3

iam = boto3.client("iam")
ROLE_ARN = sys.argv[1]
PROJECT_NAME = sys.argv[2]
ROLE_NAME = f"seedfarmer-{PROJECT_NAME}-toolchain-role"


trusted_principals = iam.get_role(RoleName=ROLE_NAME)["Role"][
    "AssumeRolePolicyDocument"
]["Statement"][0]["Principal"]["AWS"]
if type(trusted_principals) is not list:
    trusted_principals = [trusted_principals]
    print(
        f"Current principals in assume role policy for {ROLE_NAME}: {trusted_principals}"
    )

principals = []
for principal in trusted_principals:
    if "arn:" not in principal:
        print(f"Removing non-existent principal: {principal}")
    else:
        principals.append(principal)

if ROLE_ARN not in principals:
    print(f"{ROLE_ARN} not in trusted principals list and will be added.")
    principals.append(ROLE_ARN)

policy_document = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": principals},
                "Action": ["sts:AssumeRole"],
            }
        ],
    }
)
try:
    response = iam.update_assume_role_policy(
        RoleName=ROLE_NAME,
        PolicyDocument=policy_document,
    )
    print("Success")
except Exception as e:
    print(f"issue updating assume role policy document: {e}")
    raise e
