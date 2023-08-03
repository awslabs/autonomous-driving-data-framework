import sys
import yaml

if len(sys.argv) != 4:
    print(
        "Usage: python manifest-update.py [TOOLCHAIN REGION] [TARGET REGION] [TARGET ACCOUNT]"
    )
    exit(1)

toolchain_region = sys.argv[1]
target_region = sys.argv[2]
target_account = sys.argv[3]
with open("idf-modules.yaml", "r") as file:
    data = yaml.safe_load(file)

data["toolchainRegion"] = toolchain_region
data["targetAccountMappings"][0]["accountId"] = target_account
data["targetAccountMappings"][0]["regionMappings"][0]["region"] = target_region

with open("deployment.yaml", "w") as file:
    yaml.dump(data, file)

print(
    f"manifest has been updated and seedfarmer will deploy the following: \n{open('deployment.yaml').read()}"
)
