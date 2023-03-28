import json
import os

import boto3

# ADDF Variables
deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")

# ADDF Parameters
custom_kernel_name = os.getenv("ADDF_PARAMETER_CUSTOM_KERNEL_NAME", "")
image_name = os.getenv("ADDF_PARAMETER_SAGEMAKER_IMAGE_NAME")
app_image_config_name = os.getenv("ADDF_PARAMETER_APP_IMAGE_CONFIG_NAME")
sm_studio_domain_id = os.environ.get("ADDF_PARAMETER_STUDIO_DOMAIN_ID")
sm_studio_domain_name = os.environ.get("ADDF_PARAMETER_STUDIO_DOMAIN_NAME")
uid = os.getenv("ADDF_PARAMETER_KERNEL_USER_UID", 1000)
gid = os.getenv("ADDF_PARAMETER_KERNEL_USER_GID", 100)
mount_path = os.getenv("ADDF_PARAMETER_KERNEL_USER_HOME_MOUNT_PATH", "/home/sagemaker-user")

# CDK Export
cdk_exports_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "cdk-exports.json")
cdk_output_file = open(cdk_exports_path)
cdk_output = json.load(cdk_output_file)
app_prefix = f"addf-{deployment_name}-{module_name}"
role_arn = cdk_output[app_prefix]["SageMakerCustomKernelRoleArn"]

# Deployspec ENV vars
ecr_repository_uri = os.getenv("REPOSITORY_URI")
image_uri = os.getenv("IMAGE_URI")

# Config vars
display_name = image_name  # Should stay same to allow config mapping in update_domain
sm_client = boto3.client("sagemaker")
tags = [
    {"Key": "CreatedBy", "Value": "ADDF"},
    {"Key": "ModuleName", "Value": module_name},
    {"Key": "DeploymentName", "Value": deployment_name},
]


def create_image():
    return sm_client.create_image(
        Description="ADDF Generated Image",
        DisplayName=display_name,
        ImageName=image_name,
        RoleArn=role_arn,
        Tags=tags,
    )


def create_image_if_not_exist():
    print("Attempting to create Image:", image_name)
    try:
        image = create_image()
        print("Image Created:", image)
    except Exception as e:
        print(f"Warning: already exists [error: {e}]. Skipping creation...")


def create_image_version():
    sm_client.create_image_version(
        BaseImage=image_uri,
        ImageName=image_name,
    )

    return sm_client.describe_image_version(ImageName=image_name)


def check_image_version_exists():
    try:
        describe_last_image_version_response = sm_client.describe_image_version(ImageName=image_name)
        if describe_last_image_version_response["BaseImage"] == image_uri:
            return (True, describe_last_image_version_response)
        else:
            return (False, describe_last_image_version_response)
    except Exception as e:
        print(f"No versions exist [error: {e}]. Need to create")
        return (False, None)


def create_image_version_if_not_exists():
    print("Attempting to create image version with BaseImage:", image_uri)
    exists, last_version = check_image_version_exists()
    print("Last Image Version:", last_version)
    if not exists:
        image_version = create_image_version()
        print("Updated Image Version:", image_version)
    else:
        print("Exists. Skipping create_image_version....")


def check_app_image_config_exists():
    try:
        response = sm_client.describe_app_image_config(AppImageConfigName=app_image_config_name)
        return (True, response)
    except Exception:
        return (False, None)


def create_app_image_config():
    return sm_client.create_app_image_config(
        AppImageConfigName=app_image_config_name,
        Tags=tags,
        KernelGatewayImageConfig={
            "KernelSpecs": [
                {
                    "Name": custom_kernel_name,
                    "DisplayName": image_name,
                },
            ],
            "FileSystemConfig": {
                "MountPath": mount_path,
                "DefaultUid": int(uid),
                "DefaultGid": int(gid),
            },
        },
    )


def update_app_image_config():
    return sm_client.update_app_image_config(
        AppImageConfigName=app_image_config_name,
        KernelGatewayImageConfig={
            "KernelSpecs": [
                {
                    "Name": custom_kernel_name,
                    "DisplayName": image_name,
                },
            ],
            "FileSystemConfig": {
                "MountPath": mount_path,
                "DefaultUid": int(uid),
                "DefaultGid": int(gid),
            },
        },
    )


def create_app_image_config_if_not_exists():
    print("Attempting to create App Image Config:", app_image_config_name)
    try:
        exists, existing_config = check_app_image_config_exists()
        print("Existing App Image Config:", existing_config)
        if not exists:
            created_config = create_app_image_config()
            print("Created Image Config:", created_config)
        else:
            updated_config = update_app_image_config()
            print("Updated Image Config:", updated_config)
    except Exception as e:
        print("Failed to create or update App Image Config")
        raise e


def update_domain():
    try:
        domain = sm_client.describe_domain(
            DomainId=sm_studio_domain_id,
        )

        print("current_domain", domain)

        default_user_settings = domain["DefaultUserSettings"]
        if "KernelGatewayAppSettings" not in default_user_settings:
            default_user_settings["KernelGatewayAppSettings"] = {}
        kernel_gateway_app_settings = default_user_settings["KernelGatewayAppSettings"]
        existing_custom_images = kernel_gateway_app_settings.get("CustomImages", [])

        # Custom Image config we'd like to attach to Studio
        new_custom_image = {
            "ImageName": image_name,
            "AppImageConfigName": app_image_config_name,
        }

        existing_custom_images.append(new_custom_image)
        merged_distinct_custom_images = list(
            dict((v["AppImageConfigName"], v) for v in existing_custom_images).values(),
        )
        default_user_settings["KernelGatewayAppSettings"]["CustomImages"] = merged_distinct_custom_images

        print(f"Updating Sagemaker Studio Domain - {sm_studio_domain_name} ({sm_studio_domain_id})")
        print(default_user_settings)
        sm_client.update_domain(
            DomainId=sm_studio_domain_id,
            DefaultUserSettings=default_user_settings,
        )
    except Exception as e:
        print("Error updating studio domain")
        raise e


def print_step(step):
    print(f'{"-" * 35} {step} {"-" * 35}')


if __name__ == "__main__":
    print_step("Create Image")
    create_image_if_not_exist()
    print_step("Create Image Version")
    create_image_version_if_not_exists()
    print_step("Create App Config")
    create_app_image_config_if_not_exists()
    print_step("Attach to Studio Domain")
    update_domain()
    print_step("Create Kernel Complete")
