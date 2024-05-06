import sys

import yaml

if len(sys.argv) != 5:
    print(
        "Usage: python manifest-update.py [MANIFEST PATH][TOOLCHAIN REGION] [TARGET REGION] [TARGET ACCOUNT]"
    )
    exit(1)

manifest_path = sys.argv[1].strip('\"')
print(f"mainfest path: {manifest_path}")
toolchain_region = sys.argv[2]
target_region = sys.argv[3]
target_account = sys.argv[4]
with open(manifest_path, "r") as file:
    data = yaml.safe_load(file)

data["toolchainRegion"] = toolchain_region
data["targetAccountMappings"][0]["accountId"] = target_account
data["targetAccountMappings"][0]["regionMappings"][0]["region"] = target_region

with open("deployment.yaml", "w") as file:
    yaml.dump(data, file)

print(
    f"manifest has been updated and seedfarmer will deploy the following: \n{open('deployment.yaml').read()}"
)
