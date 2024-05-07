import sys

import yaml

if len(sys.argv) != 2:
    print("Usage: python get_manifest_deployment_name.py [MANIFEST PATH]")
    exit(1)

manifest_path = sys.argv[1].strip('"')
with open(manifest_path, "r") as file:
    data = yaml.safe_load(file)

print(data["name"])
