import boto3, json, yaml, os
from passlib.hash import bcrypt; 
from typing import Dict,List
import random, re

client = boto3.client("secretsmanager")
project_name = os.getenv("AWS_CODESEEDER_NAME","addf")
account_id=os.getenv("AWS_ACCOUNT_ID","123456789012")

def get_sample_users()->Dict:
    return [
        {"email":"user1@amazon.com","policyArn":f"arn:aws:iam::{account_id}:role/AdminRole"},
        {"email":"user2@gmail.com","policyArn":f"arn:aws:iam::{account_id}:role/AdminRole"}
    ]

def _proj(name: str) -> str:
    return f"{project_name.upper()}_{name}"

def _param(name: str) -> str:
    return f"{project_name.upper()}_PARAMETER_{name}"

deployment_name = os.getenv(_proj("DEPLOYMENT_NAME"), "")
module_name = os.getenv(_proj("MODULE_NAME"), "")

users = json.loads(os.getenv(_param("KUBEFLOW_USERS"))) if os.getenv(_param("KUBEFLOW_USERS")) else get_sample_users()


def get_payload(email:str, pwd:str, username: str)->str:
    return json.dumps({"email":email,"password":pwd,"username":username})

def create_pwd()->str:
    return client.get_random_password(
        PasswordLength=6,
        ExcludeNumbers=False,
        ExcludePunctuation=True,
        ExcludeUppercase=False,
        ExcludeLowercase=False,
        IncludeSpace=False,
    )['RandomPassword']

def get_pwd(email:str, secretname:str, username: str)->str:
    try:
        re = client.describe_secret(SecretId=secretname)
        response = client.get_secret_value(SecretId=secretname)
        secret_string = response['SecretString']
        pwd = json.loads(secret_string)['password']
        return bcrypt.using(rounds=12, ident="2y").hash(pwd)

    except client.exceptions.ResourceNotFoundException:
        print("create new secret and pwd")
        pwd = create_pwd()
        response = client.create_secret(
            Name=secretname,
            SecretString=get_payload(email,pwd,username)
        )
        return bcrypt.using(rounds=12, ident="2y").hash(pwd)
    except Exception as e:
        print(e)
        exit(1)

def generate_profile(email:str, policy_arn:str, username: str)-> None:
    with open('profiles/profile.template', 'r') as file:
        profile = yaml.safe_load(file)
    profile['metadata']['name']=username
    profile['spec']['owner']['name']=email
    if policy_arn:
        plugins=[]
        plugins.append({'kind': 'AwsIamForServiceAccount','spec':{'awsIamRole':policy_arn}})
        profile['spec']['plugins']= plugins

    with open(f'profiles/{username}-profile.yaml', 'w') as file:
        yaml.dump(profile,file)


def generate_config(info:List[Dict[str,str]])->None:
    
    with open('kustomize/config.template', 'r') as file:
        config_map = yaml.safe_load(file)
    config_map['staticPasswords']=info
    with open(f'kustomize/config.yaml', 'w') as file:
        yaml.dump(config_map,file)

def write_metadata(metadata_users:List[str])->None:
    metadata={'metadata':{"KubeflowUsersDeployed":metadata_users}}
    with open(f'kf-exports.json', 'w') as file:
        json.dump(metadata,file)

def create():
    kustomize_map = []
    user_metadata = {}
    for user in users:
        email=user['email']
        username=re.sub(r'\W+', '', email.split('@')[0])
        secret_name=f"{project_name}-{deployment_name}-{module_name}-kf-{username}"
        user={"secretname":secret_name,"email":email,"username":username}
        policy_arn=user['policyArn'] if user.get('policyArn') else None        
        encoded_pwd=get_pwd(**user)
        kustomize_map.append({
            "email":email,
            "hash":encoded_pwd,
            "username":username,
            "userID":str(random.randint(10000, 900000))
        })
        generate_profile(email,policy_arn,username)
        user_metadata[username]=user
    generate_config(kustomize_map)
    write_metadata(user_metadata)


if __name__=='__main__':
    create()

