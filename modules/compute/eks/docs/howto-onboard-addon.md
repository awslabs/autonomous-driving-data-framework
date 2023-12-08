# How to onboard the EKS Addon 

1. Add the chart from the public repository in the dockerimage-replication module in the `default.yaml` file of the versions directory. 
    
2. Check the latest stable release from the public helm repository, add that version in the default.yaml
    
3. Check for the images in the values.yaml of the public helm repository, add those images in add-on specification in the `default.yaml`. 
    
4. Add the location and path of the repository in the add-on specification.

```yaml
    images:
      <image-name>:
        repository:
          location: values
          path: image.repository
```

5. Add the tag of the image in the add-on specification

Note: Override the image tag to deploy by setting this variable, If no value is set, the chart's appVersion will be used, like the example below

```yaml
        tag:
          location: chart
          path: appVersion
```

otherwise the tag values would be in the below format. 

```yaml
        tag:
          location: values
          path: image.tag
```

6. For reference see the below the [default.yaml](https://github.com/jasaws1048/autonomous-driving-data-framework/blob/main/data/eks_dockerimage-replication/versions/default.yaml) file for addons. 

7. Add the stable repository version under chart version specification in the all the eks `k8s-version.yaml` file

8. Add the helm chart in the eks cluster, specify all the values of the helm chart which are required for deployment of the add-on. 


## There are two ways to populate the helm values:

`1. Browser`: Inspecting the public github repository for the add on. 

* Browse for the open source add on repository over the internet. 

* Check for the latest stable version in the tags section, add that version in the files(default.yaml & 1.25.yaml, etc) in the versions directory. 

* Go to charts folder, check for the values.yaml. Check for the image in the images specification and add those images in the (default.yaml & 1.25.yaml, etc). 


`2. Terminal`: Inspecting the images, values locally through the terminal 

* Adding the repository locally: 

```bash
    helm repo add [NAME] [URL] [flags]
```

for example, adding the cert-manager repository locally, use the command:

```bash
    helm repo add jetstack https://charts.jetstack.io
```

The following result will be displayed when the repository is successfully added.

```bash
    "jetstack" has been added to your repositories
```

* Listing the added the repositories, to verify the repository is added locally 

```bash
    helm repo list [flags]
```

```bash
    helm repo list -o yaml
```

The following result be displayed to show list of repositories added locally:

```yaml
- name: jetstack
  url: https://charts.jetstack.io
 ```

* Identifying the images required for the helm chart:

    Checking the charts in repository:

```bash
    helm search repo jetstack
```

#### Commands to get the chart values:

```bash
helm show values [CHART] [flags]
```

* Inspecting the images and their path required to fill in the default.yaml

```bash
helm show values jetstack/cert-manager
```

* The images in the output will be added to the default.yaml and their location and path would be according to the path in chart. 

```bash
helm show values jetstack/cert-manager | grep repository
```

### Useful Helm commands:

#### Searching for specific chart 

```bash
helm search hub jetstack
```
```bash
helm show chart [CHART] [flags]
```
