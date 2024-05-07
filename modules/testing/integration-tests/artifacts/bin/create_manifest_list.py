import sys
from typing import List


if len(sys.argv) > 1:
    manifests: List[str] = list(sys.argv[1].strip('"').split(","))
else:
    print("")
    exit()

output: str = ""
for manifest in manifests:
    manifest.strip(" ")
    output += f'"{manifest}" '

print(output)
