from typing import List

import aws_cdk as core
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sagemaker as sagemaker
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk.custom_resources import Provider
from constructs import Construct
from helper_constructs.networking import Networking
from helper_constructs.sm_roles import SMRoles


class SagemakerStudioStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        deployment_name: str,
        module_name: str,
        vpc_id: str,
        subnet_ids: List[str],
        studio_domain_name: str,
        studio_bucket_name: str,
        data_science_users: List[str],
        lead_data_science_users: List[str],
        app_image_config_name,
        image_name,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        app_prefix = f"addf-{deployment_name}-{module_name}"
        networking = Networking(
            self,
            f"{app_prefix}-networking-construct",
            vpc_id=vpc_id,
            subnet_ids=subnet_ids,
        )

        vpc = networking.vpc
        subnets = networking.subnets

        domain_name = studio_domain_name

        s3_bucket_prefix = studio_bucket_name

        # create roles to be used for sagemaker user profiles and attached to sagemaker studio domain
        self.sm_roles = SMRoles(self, "sm-roles", s3_bucket_prefix, kwargs["env"])

        # setup security group to be used for sagemaker studio domain
        sagemaker_sg = ec2.SecurityGroup(
            self,
            "SecurityGroup",
            vpc=vpc,
            description="Security Group for SageMaker Studio Notebook, Training Job and Hosting Endpoint",
        )

        sagemaker_sg.add_ingress_rule(sagemaker_sg, ec2.Port.all_traffic())

        # create sagemaker studio domain
        self.studio_domain = self.sagemaker_studio_domain(
            domain_name,
            self.sm_roles.sagemaker_studio_role,
            vpc_id=vpc.vpc_id,
            security_group_ids=[sagemaker_sg.security_group_id],
            subnet_ids=[subnet.subnet_id for subnet in subnets],
            app_image_config_name=app_image_config_name,
            image_name=image_name,
        )

        self.enable_sagemaker_projects(
            [
                self.sm_roles.sagemaker_studio_role.role_arn,
                self.sm_roles.data_scientist_role.role_arn,
                self.sm_roles.lead_data_scientist_role.role_arn,
            ],
        )

        [
            sagemaker.CfnUserProfile(
                self,
                f"ds-{user}",
                domain_id=self.studio_domain.attr_domain_id,
                user_profile_name=user,
                user_settings=sagemaker.CfnUserProfile.UserSettingsProperty(
                    execution_role=self.sm_roles.data_scientist_role.role_arn,
                ),
            )
            for user in data_science_users
        ]

        [
            sagemaker.CfnUserProfile(
                self,
                f"lead-ds-{user}",
                domain_id=self.studio_domain.attr_domain_id,
                user_profile_name=user,
                user_settings=sagemaker.CfnUserProfile.UserSettingsProperty(
                    execution_role=self.sm_roles.lead_data_scientist_role.role_arn,
                ),
            )
            for user in lead_data_science_users
        ]

    def enable_sagemaker_projects(self, roles):
        event_handler = PythonFunction(
            self,
            "sg-project-function",
            runtime=lambda_.Runtime.PYTHON_3_8,
            entry="functions/sm_studio/enable_sm_projects",
            timeout=core.Duration.seconds(120),
        )

        event_handler.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sagemaker:EnableSagemakerServicecatalogPortfolio",
                    "servicecatalog:ListAcceptedPortfolioShares",
                    "servicecatalog:AssociatePrincipalWithPortfolio",
                    "servicecatalog:AcceptPortfolioShare",
                    "iam:GetRole",
                ],
                resources=["*"],
            ),
        )

        provider = Provider(
            self,
            "sg-project-lead-provider",
            on_event_handler=event_handler,
        )

        core.CustomResource(
            self,
            "cs-sg-project",
            service_token=provider.service_token,
            removal_policy=core.RemovalPolicy.DESTROY,
            resource_type="Custom::EnableSageMakerProjects",
            properties={
                "iteration": 1,
                "ExecutionRoles": roles,
            },
        )

    def sagemaker_studio_domain(
        self,
        domain_name,
        sagemaker_studio_role,
        security_group_ids,
        subnet_ids,
        vpc_id,
        app_image_config_name,
        image_name,
    ):
        """
        Create the SageMaker Studio Domain

        :param domain_name: - name to assign to the SageMaker Studio Domain
        :param s3_bucket: - S3 bucket used for sharing notebooks between users
        :param sagemaker_studio_role: - IAM Execution Role for the domain
        :param security_group_ids: - list of comma separated security group ids
        :param subnet_ids: - list of comma separated subnet ids
        :param vpc_id: - VPC Id for the domain
        """
        custom_kernel_settings = {}
        if app_image_config_name is not None and image_name is not None:
            custom_kernel_settings[
                "kernel_gateway_app_settings"
            ] = sagemaker.CfnDomain.KernelGatewayAppSettingsProperty(
                custom_images=[
                    sagemaker.CfnDomain.CustomImageProperty(
                        app_image_config_name=app_image_config_name,
                        image_name=image_name,
                    ),
                ],
            )

        return sagemaker.CfnDomain(
            self,
            "sagemaker-domain",
            auth_mode="IAM",
            app_network_access_type="VpcOnly",
            default_user_settings=sagemaker.CfnDomain.UserSettingsProperty(
                execution_role=sagemaker_studio_role.role_arn,
                security_groups=security_group_ids,
                sharing_settings=sagemaker.CfnDomain.SharingSettingsProperty(),  # disable notebook output sharing,
                **custom_kernel_settings,
            ),
            domain_name=domain_name,
            subnet_ids=subnet_ids,
            vpc_id=vpc_id,
        )
