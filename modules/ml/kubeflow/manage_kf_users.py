import boto3, json, yaml, os
from passlib.hash import bcrypt; 
from typing import Dict,List
import random, re

sample_users = [
    {"email":"dgraeber@amazon.com","policyArn":"arn:aws:iam::616260033377:role/AdminRole"},
    {"email":"dgrabs1@gmail.com","policyArn":"arn:aws:iam::616260033377:role/AdminRole"},
    {"email":"derek.graeber@gmail.com","policyArn":"arn:aws:iam::616260033377:role/AdminRole"}
]


client = boto3.client("secretsmanager")
secret_name = 'aws-addf-docker-credentials'

project_name = os.getenv("AWS_CODESEEDER_NAME","addf")
deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME","test")
module_name = os.getenv("ADDF_MODULE_NAME","test")


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

def get_pwd(email:str, secret_name:str, username: str)->str:
    try:
        re = client.describe_secret(SecretId=secret_name)
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response['SecretString']
        pwd = json.loads(secret_string)['password']
        return bcrypt.using(rounds=12, ident="2y").hash(pwd)

    except client.exceptions.ResourceNotFoundException:
        print("create new secret and pwd")
        pwd = create_pwd()
        response = client.create_secret(
            Name=secret_name,
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

def create():
    kustomize_map = []
    for user in sample_users:
        email=user['email']
        username=re.sub(r'\W+', '', email.split('@')[0])
        secret_name=f"{project_name}-{deployment_name}-{module_name}-kf-{username}"
        policy_arn=user['policyArn'] if user.get('policyArn') else None

        encoded_pwd=get_pwd(email,secret_name,username)
        kustomize_map.append({
            "email":email,
            "hash":encoded_pwd,
            "username":username,
            "userID":str(random.randint(10000, 900000))
        })
        generate_profile(email,policy_arn,username)
    generate_config(kustomize_map)

if __name__=='__main__':
    create()

