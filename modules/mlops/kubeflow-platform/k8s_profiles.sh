#!/bin/bash

rm -f profiles.out || true
kubectl get profiles -o json |  jq -r '.items[].metadata.name' >> profiles.out
for name in $(cat profiles.out); do kubectl patch profile $name --type json -p '{"metadata":{"finalizers":null}}' --type=merge; done  || true
