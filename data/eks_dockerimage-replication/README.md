# Description

The data files added here will be consumed between `EKS` module and `Docker replication` module.

Docker replicaton module conditionally consumes these files and replicates the images into AWS ECR.

EKS module consumes the data inside these files and scrapes the helm chart locations, image references etc.