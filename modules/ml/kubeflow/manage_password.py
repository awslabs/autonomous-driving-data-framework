import boto3, json, yaml
from passlib.hash import bcrypt; 




client = boto3.client("secretsmanager")
secret_name = 'aws-addf-docker-credentials2'

PWD = "pwd-placeholder"
EMAIL = "email-placeholder"
payload = {"email":EMAIL,"password":PWD}

def get_payload(email:str, pwd:str)->str:
    return json.dumps(payload).replace(PWD,pwd).replace(EMAIL,email)

def create_pwd()->str:
    return client.get_random_password(
        PasswordLength=6,
        ExcludeNumbers=False,
        ExcludePunctuation=True,
        ExcludeUppercase=False,
        ExcludeLowercase=False,
        IncludeSpace=False,
    )['RandomPassword']

def get_pwd(email:str, secret_name:str, replace:bool=False)->str:
    try:
        replace_pwd = False
        re = client.describe_secret(SecretId=secret_name)
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response['SecretString']
        pwd = json.loads(secret_string)['password']
        secret_arn=response['ARN']
        print(secret_string)
        if replace_pwd:
            pwd = create_pwd()
            client.put_secret_value(
                SecretId=secret_arn,
                SecretString=get_payload(email,pwd)
            )
        return bcrypt.using(rounds=12, ident="2y").hash(pwd)

    except client.exceptions.ResourceNotFoundException:
        print("create it")
        response = client.create_secret(
            Name=secret_name,
            SecretString=get_payload(email,pwd)
        )


    except Exception as e:
        print(e)
        exit(1)

#print(bcrypt.using(rounds=12, ident="2y").hash("Mypassword1!"))
# with open('/Users/dgraeber/aws-seed-group/autonomous-driving-data-framework/modules/ml/kubeflow/upstream/common/dex/base/config-map.yaml', 'r') as file:
#    config_map = yaml.safe_load(file)

# maps = config_map['data']['config.yaml']
# con = yaml.safe_load(maps)
# print(con)

# newvals = [
#     {
#       "email":"user1@gmail.com",
#       "hash": "$2y$12$4K/VkmDd1q1Orb3xAt82zu8gk7Ad6ReFR4LCP9UeYE90NLiN9Df72",
#       "username": "user1",
#       "userID": "15841185641784"
#     },
#     {
#       "email":"user1@gmail.com",
#       "hash": "$2y$12$4K/VkmDd1q1Orb3xAt82zu8gk7Ad6ReFR4LCP9UeYE90NLiN9Df72",
#       "username": "user2",
#       "userID": "15841185641785"
#     },
#     {
#       "email":"user3@gmail.com",
#       "hash": "$2y$12$4K/VkmDd1q1Orb3xAt82zu8gk7Ad6ReFR4LCP9UeYE90NLiN9Df72",
#       "username": "user3",
#       "userID": "15841185641786"
#     }
# ]



# con['staticPasswords']=newvals
# config_map['data']['config.yaml']=con

# with open('/Users/dgraeber/aws-seed-group/autonomous-driving-data-framework/modules/ml/kubeflow/upstream/common/dex/base/config-map-out.yaml', 'w') as file:
#    yaml.dump(con,file)

# config_map['data']['config.yaml']="config-map-out.yaml"
# with open('/Users/dgraeber/aws-seed-group/autonomous-driving-data-framework/modules/ml/kubeflow/upstream/common/dex/base/config-map-out_redo.yaml', 'w') as file:
#    yaml.dump(config_map,file)

with open('/Users/dgraeber/aws-seed-group/autonomous-driving-data-framework/modules/ml/kubeflow/upstream/common/dex/base/config-map-out_redo.yaml', 'r') as file:
   config_map_r = yaml.safe_load(file)

print(config_map_r)