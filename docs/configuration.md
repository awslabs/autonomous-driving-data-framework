# Deployment and Configuration of Addons on EKS

- `default.yaml`: This is configuration file specifying the default version of EKS Addons to be deployed

- `k8s-version.yaml`(This is named after a specific EKS version): This file is a version-specific configuration file for EKS Addons.It contains specific configuration values relevant to EKS version 1.25, 1.24, etc.

- `stack.py`: This reads the default.yaml file to determine the default version of EKS Addon to be deployed. This version is used later when adding the Helm chart for Addon to the EKS cluster.

## How the script

### Uses the data from the configuration files

The Python script `stack.py` reads the `default.yaml` file to determine the default version of Addon to be deployed. This version is used later when adding the Helm chart for Addon to the EKS cluster. The script defines the container image details within the `stack.py` file itself. These details include the repository URLs and tags for different Addon components. The script uses these details to specify the container images when deploying Addon via the Helm chart.

### Inspects the registries

The script doesn't directly inspect the registries. Instead, it relies on the container image details provided in the `stack.py` file to identify the repository URLs and tags. These details are pre-determined based on the desired versions and sources of Addon components.

### Grabs the container image details

1. The Python script utilizes a configuration file called `stack.py` to define and retrieve container image details for deploying Addons on an EKS cluster. Within the `stack.py` file, there is a section specifically dedicated to each addon.

2. Under that addon section, various addon components are listed, along with their corresponding container image details. Each component includes two key-value pairs: repository and tag.

3. The repository value specifies the URL of the container image repository where the component's image is located. The tag value indicates the specific tag or version of the container image.

4. To access the container image details, the Python script uses appropriate expressions to retrieve the values from the `stack.py` file. By navigating the dictionary structure of the addon section and accessing the specific component, the script can retrieve the repository URL and tag for each addon component.

5. Once the script has obtained these container image details, it can utilize them in various deployment operations. For example, the script may use the repository URL and tag when adding the Helm chart for addon to the EKS cluster, ensuring the correct container images are pulled and deployed.

6. By leveraging the container image details defined in the `stack.py` file, the Python script can accurately identify and utilize the desired addon container images, streamlining the deployment process on the EKS cluster.

### Replicates images to ECR

replication.sh is used to replicate the images to ECR. The detailed description of the script:

1. The script defines two main functions: `create` and `destroy`. The create function is responsible for pulling the container images, tagging them, and pushing them to ECR.

2. The create function reads a file named `images.txt` line by line, where each line represents a container image to be replicated to ECR. The read command is used to read each line into the image variable.

3. Within the loop, the script extracts the image name and tag using awk command. The `image_name` variable stores the image name, and the `image_tag` variable stores the image tag.

4. If the image name starts with a number (checked using a regular expression), it indicates that the image is hosted on a different registry. In this case, the script retrieves the login password for the AWS ECR using the `aws ecr get-login-password` command and logs in to the corresponding ECR repository using docker login.

5. The script pulls the container image using docker pull and sets up the connection with the AWS ECR repository.

6. It then checks if the repository for the image exists in the AWS ECR. If it does not exist, it creates a new repository using the `aws ecr create-repository` command.

7. The script performs another login to the AWS ECR using docker login to ensure it has the necessary credentials to push the image.

8. The script tags the pulled container image with the ECR repository URL and the appropriate tag using docker tag.

9. It pushes the tagged image to the ECR repository using docker push.

10. Finally, the script deletes the pulled container image using docker rmi to free up space and avoid issues with CodeBuild storage.

In summary, the script iterates over the lines in the `images.txt` file, pulls each container image, tags it with the appropriate ECR repository URL and tag, and then pushes it to the ECR repository specified by the AWS account.