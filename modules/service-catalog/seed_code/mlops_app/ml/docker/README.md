## Custom SageMaker PyTorch Framework Processor Container

The Dockerfile here shows how to extend the base pytorch framework processor. You can find other base docker images from SageMaker on [Deep Learning Containers GitHub Page](https://github.com/aws/deep-learning-containers/blob/master/available_images.md#sagemaker-framework-containers-sm-support-only)


## Building custom containers

***NOTE: Currently, containers can't be built inside SageMaker Studio. Please build the image locally or using the [Sagemaker Studio Image Build CLI Blog](https://aws.amazon.com/blogs/machine-learning/using-the-amazon-sagemaker-studio-image-build-cli-to-build-container-images-from-your-studio-notebooks/) / [Github](https://github.com/aws-samples/sagemaker-studio-image-build-cli)***

To be able to pull the base image from the SageMaker Service Team's ECR repository, you first need to log into their public ECR account (763104351884) with docker

```
$ aws ecr get-login-password --region <YOUR_REGION> | docker login --username AWS --password-stdin 763104351884.dkr.ecr.<YOUR_REGION>.amazonaws.com
```

Once you've logged into the account, you can build the docker image as normally

```
$ docker build -t custom-sm-container .
```

## Pushing Images to ECR

To use your images in SageMaker, you need to push them to an ECR repository. You can add an ECR repository for your project in the CDK code under the `./infra` folder. 

[CDK ECR Construct Docs](https://docs.aws.amazon.com/cdk/api/v1/docs/aws-ecr-readme.html)

Once your repository has been created, you can log into it from docker:

```
$ aws ecr get-login-password --region <YOUR_REGION> | docker login --username AWS --password-stdin <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com
```

Tag your images and push

```
$ docker tag custom-sm-container <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/<YOUR_ECR_REPO_NAME>:<TAG>
$ docker push <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/<YOUR_ECR_REPO_NAME>:<TAG>
```