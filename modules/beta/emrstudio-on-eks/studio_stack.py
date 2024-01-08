# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# type: ignore

import random
from typing import List, cast

import cdk_nag
from aws_cdk import Aspects, CfnOutput, Stack, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_emr as emr
from aws_cdk import aws_emrcontainers as emrc
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import custom_resources as custom
from cdk_nag import NagSuppressions
from constructs import Construct, IConstruct
from OpenSSL import crypto

"""
This stack deploys the following:
- EMR on EKS virtual cluster
- EMR Studio
"""


class StudioLiveStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        deployment: str,
        module: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        artifact_bucket_name: str,
        eks_cluster_name: str,
        execution_role_arn: str,
        emr_namespace: str,
        sso_username: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, description="This stack deploys EMR Studio for ADDF", **kwargs)
        dep_mod = f"addf-{deployment}-{module}"
        dep_mod = dep_mod[:27]

        Tags.of(scope=cast(IConstruct, self)).add(key="Deployment", value=f"addf-{deployment}")

        # EMR virtual cluster
        self.emr_vc = emrc.CfnVirtualCluster(
            scope=self,
            id=f"{dep_mod}-EMRVirtualCluster",
            container_provider=emrc.CfnVirtualCluster.ContainerProviderProperty(
                id=eks_cluster_name,
                info=emrc.CfnVirtualCluster.ContainerInfoProperty(
                    eks_info=emrc.CfnVirtualCluster.EksInfoProperty(namespace=emr_namespace)
                ),
                type="EKS",
            ),
            name=f"{dep_mod}-EMRCluster",
        )

        # policy to let Lambda invoke the api
        custom_policy_document = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:CreateSecurityGroup",
                        "ec2:RevokeSecurityGroupEgress",
                        "ec2:CreateSecurityGroup",
                        "ec2:DeleteSecurityGroup",
                        "ec2:AuthorizeSecurityGroupEgress",
                        "ec2:AuthorizeSecurityGroupIngress",
                        "ec2:RevokeSecurityGroupIngress",
                        "ec2:DeleteSecurityGroup",
                    ],
                    resources=["*"],
                )
            ]
        )
        managed_policy = iam.ManagedPolicy(self, f"{id}-ManagedPolicy", document=custom_policy_document)

        self.role = iam.Role(
            scope=self,
            id=f"{id}-LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                managed_policy,
            ],
        )

        # cert for endpoint
        crt, pkey = self.cert_gen(serialNumber=random.randint(1000, 10000))
        mycert = custom.AwsCustomResource(
            self,
            f"{id}-CreateCert",
            on_update={
                "service": "ACM",
                "action": "importCertificate",
                "parameters": {"Certificate": crt.decode("utf-8"), "PrivateKey": pkey.decode("utf-8")},
                "physical_resource_id": custom.PhysicalResourceId.from_response("CertificateArn"),
            },
            policy=custom.AwsCustomResourcePolicy.from_sdk_calls(resources=custom.AwsCustomResourcePolicy.ANY_RESOURCE),
            role=self.role,
            function_name="CreateCertFn",
        )

        # Set up managed endpoint for Studio
        endpoint = custom.AwsCustomResource(
            self,
            f"{id}-CreateEndpoint",
            on_create={
                "service": "EMRcontainers",
                "action": "createManagedEndpoint",
                "parameters": {
                    "certificateArn": mycert.get_response_field("CertificateArn"),
                    "executionRoleArn": execution_role_arn,
                    "name": "emr-endpoint-eks-spark",
                    "releaseLabel": "emr-6.2.0-latest",
                    "type": "JUPYTER_ENTERPRISE_GATEWAY",
                    "virtualClusterId": self.emr_vc.attr_id,
                },
                "physical_resource_id": custom.PhysicalResourceId.from_response("arn"),
            },
            policy=custom.AwsCustomResourcePolicy.from_sdk_calls(resources=custom.AwsCustomResourcePolicy.ANY_RESOURCE),
            role=self.role,
            function_name="CreateEpFn",
        )
        endpoint.node.add_dependency(mycert)

        # Studio live

        # ArtifactBucket for backing Workspace and notebook files
        bucket = s3.Bucket.from_bucket_name(self, f"{id}-artifacts-bucket", artifact_bucket_name)

        self.vpc_id = vpc_id
        self.vpc = ec2.Vpc.from_lookup(
            self,
            "VPC",
            vpc_id=vpc_id,
        )

        self.private_subnets = []
        for idx, subnet_id in enumerate(private_subnet_ids):
            self.private_subnets.append(ec2.Subnet.from_subnet_id(scope=self, id=f"subnet{idx}", subnet_id=subnet_id))

        # Create security groups
        eng_sg = ec2.SecurityGroup(
            self, "EngineSecurityGroup", vpc=self.vpc, description="EMR Studio Engine", allow_all_outbound=True
        )
        Tags.of(eng_sg).add("for-use-with-amazon-emr-managed-policies", "true")
        ws_sg = ec2.SecurityGroup(
            self, "WorkspaceSecurityGroup", vpc=self.vpc, description="EMR Studio Workspace", allow_all_outbound=False
        )
        Tags.of(ws_sg).add("for-use-with-amazon-emr-managed-policies", "true")
        ws_sg.add_egress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "allow egress on port 443")
        ws_sg.add_egress_rule(eng_sg, ec2.Port.tcp(18888), "allow egress on port 18888 to eng")
        eng_sg.add_ingress_rule(ws_sg, ec2.Port.tcp(18888), "allow ingress on port 18888 from ws")

        # Studio Service Role
        role = iam.Role(
            self,
            "StudioServiceRole",
            assumed_by=iam.ServicePrincipal("elasticmapreduce.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")],
        )
        Tags.of(role).add("for-use-with-amazon-emr-managed-policies", "true")
        role.add_to_policy(
            iam.PolicyStatement(
                resources=["*"],
                actions=[
                    "ec2:AuthorizeSecurityGroupEgress",
                    "ec2:AuthorizeSecurityGroupIngress",
                    "ec2:CreateSecurityGroup",
                    "ec2:CreateTags",
                    "ec2:DescribeSecurityGroups",
                    "ec2:RevokeSecurityGroupEgress",
                    "ec2:RevokeSecurityGroupIngress",
                    "ec2:CreateNetworkInterface",
                    "ec2:CreateNetworkInterfacePermission",
                    "ec2:DeleteNetworkInterface",
                    "ec2:DeleteNetworkInterfacePermission",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:ModifyNetworkInterfaceAttribute",
                    "ec2:DescribeTags",
                    "ec2:DescribeInstances",
                    "ec2:DescribeSubnets",
                    "ec2:DescribeVpcs",
                    "elasticmapreduce:ListInstances",
                    "elasticmapreduce:DescribeCluster",
                    "elasticmapreduce:ListSteps",
                ],
                effect=iam.Effect.ALLOW,
            )
        )

        # Studio User Role
        user_role = iam.Role(self, "StudioUserRole", assumed_by=iam.ServicePrincipal("elasticmapreduce.amazonaws.com"))
        Tags.of(role).add("for-use-with-amazon-emr-managed-policies", "true")
        user_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "elasticmapreduce:CreateEditor",
                    "elasticmapreduce:DescribeEditor",
                    "elasticmapreduce:ListEditors",
                    "elasticmapreduce:StartEditor",
                    "elasticmapreduce:StopEditor",
                    "elasticmapreduce:DeleteEditor",
                    "elasticmapreduce:OpenEditorInConsole",
                    "elasticmapreduce:AttachEditor",
                    "elasticmapreduce:DetachEditor",
                    "elasticmapreduce:CreateRepository",
                    "elasticmapreduce:DescribeRepository",
                    "elasticmapreduce:DeleteRepository",
                    "elasticmapreduce:ListRepositories",
                    "elasticmapreduce:LinkRepository",
                    "elasticmapreduce:UnlinkRepository",
                    "elasticmapreduce:DescribeCluster",
                    "elasticmapreduce:ListInstanceGroups",
                    "elasticmapreduce:ListBootstrapActions",
                    "elasticmapreduce:ListClusters",
                    "elasticmapreduce:ListSteps",
                    "elasticmapreduce:CreatePersistentAppUI",
                    "elasticmapreduce:DescribePersistentAppUI",
                    "elasticmapreduce:GetPersistentAppUIPresignedURL",
                    "secretsmanager:CreateSecret",
                    "secretsmanager:ListSecrets",
                    "secretsmanager:TagResource",
                    "emr-containers:DescribeVirtualCluster",
                    "emr-containers:ListVirtualClusters",
                    "emr-containers:DescribeManagedEndpoint",
                    "emr-containers:ListManagedEndpoints",
                    "emr-containers:CreateAccessTokenForManagedEndpoint",
                    "emr-containers:DescribeJobRun",
                    "emr-containers:ListJobRuns",
                ],
                resources=["*"],
                effect=iam.Effect.ALLOW,
            )
        )
        user_role.add_to_policy(
            iam.PolicyStatement(
                resources=["*"],
                actions=[
                    "servicecatalog:DescribeProduct",
                    "servicecatalog:DescribeProductView",
                    "servicecatalog:DescribeProvisioningParameters",
                    "servicecatalog:ProvisionProduct",
                    "servicecatalog:SearchProducts",
                    "servicecatalog:UpdateProvisionedProduct",
                    "servicecatalog:ListProvisioningArtifacts",
                    "servicecatalog:DescribeRecord",
                    "cloudformation:DescribeStackResources",
                    "kms:Decrypt",
                    "kms:GenerateDataKey",
                    "kms:ReEncryptFrom",
                    "kms:ReEncryptTo",
                    "kms:DescribeKey",
                ],
                effect=iam.Effect.ALLOW,
            )
        )
        user_role.add_to_policy(
            iam.PolicyStatement(resources=["*"], actions=["elasticmapreduce:RunJobFlow"], effect=iam.Effect.ALLOW)
        )
        user_role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    role.role_arn,
                    f"arn:aws:iam::{self.account}:role/EMR_DefaultRole",
                    f"arn:aws:iam::{self.account}:role/EMR_EC2_DefaultRole",
                ],
                actions=["iam:PassRole"],
                effect=iam.Effect.ALLOW,
            )
        )
        user_role.add_to_policy(
            iam.PolicyStatement(
                resources=["arn:aws:s3:::*"],
                actions=["s3:ListAllMyBuckets", "s3:ListBucket", "s3:GetBucketLocation"],
                effect=iam.Effect.ALLOW,
            )
        )
        user_role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    f"arn:aws:s3:::{bucket.bucket_name}",
                    f"arn:aws:s3:::{bucket.bucket_name}/*",
                    f"arn:aws:s3:::aws-logs-{self.account}-{self.region}/elasticmapreduce/*",
                ],
                actions=["s3:GetObject"],
                effect=iam.Effect.ALLOW,
            )
        )

        # User Session Mapping permissions
        policy_document = {
            "Version": "2012-10-17T00:00:00.000Z",
            "Statement": [
                {
                    "Action": [
                        "elasticmapreduce:CreateEditor",
                        "elasticmapreduce:DescribeEditor",
                        "elasticmapreduce:ListEditors",
                        "elasticmapreduce:StartEditor",
                        "elasticmapreduce:StopEditor",
                        "elasticmapreduce:DeleteEditor",
                        "elasticmapreduce:OpenEditorInConsole",
                        "elasticmapreduce:AttachEditor",
                        "elasticmapreduce:DetachEditor",
                        "elasticmapreduce:CreateRepository",
                        "elasticmapreduce:DescribeRepository",
                        "elasticmapreduce:DeleteRepository",
                        "elasticmapreduce:ListRepositories",
                        "elasticmapreduce:LinkRepository",
                        "elasticmapreduce:UnlinkRepository",
                        "elasticmapreduce:DescribeCluster",
                        "elasticmapreduce:ListInstanceGroups",
                        "elasticmapreduce:ListBootstrapActions",
                        "elasticmapreduce:ListClusters",
                        "elasticmapreduce:ListSteps",
                        "elasticmapreduce:CreatePersistentAppUI",
                        "elasticmapreduce:DescribePersistentAppUI",
                        "elasticmapreduce:GetPersistentAppUIPresignedURL",
                        "secretsmanager:CreateSecret",
                        "secretsmanager:ListSecrets",
                        "emr-containers:DescribeVirtualCluster",
                        "emr-containers:ListVirtualClusters",
                        "emr-containers:DescribeManagedEndpoint",
                        "emr-containers:ListManagedEndpoints",
                        "emr-containers:CreateAccessTokenForManagedEndpoint",
                        "emr-containers:DescribeJobRun",
                        "emr-containers:ListJobRuns",
                    ],
                    "Resource": "*",
                    "Effect": "Allow",
                    "Sid": "AllowBasicActions",
                },
                {
                    "Action": [
                        "servicecatalog:DescribeProduct",
                        "servicecatalog:DescribeProductView",
                        "servicecatalog:DescribeProvisioningParameters",
                        "servicecatalog:ProvisionProduct",
                        "servicecatalog:SearchProducts",
                        "servicecatalog:UpdateProvisionedProduct",
                        "servicecatalog:ListProvisioningArtifacts",
                        "servicecatalog:DescribeRecord",
                        "cloudformation:DescribeStackResources",
                    ],
                    "Resource": "*",
                    "Effect": "Allow",
                    "Sid": "AllowIntermediateActions",
                },
                {
                    "Action": ["elasticmapreduce:RunJobFlow"],
                    "Resource": "*",
                    "Effect": "Allow",
                    "Sid": "AllowAdvancedActions",
                },
                {
                    "Action": "iam:PassRole",
                    "Resource": [
                        role.role_arn,
                        f"arn:aws:iam::{self.account}:role/EMR_DefaultRole",
                        f"arn:aws:iam::{self.account}:role/EMR_EC2_DefaultRole",
                    ],
                    "Effect": "Allow",
                    "Sid": "PassRolePermission",
                },
                {
                    "Action": ["s3:ListAllMyBuckets", "s3:ListBucket", "s3:GetBucketLocation"],
                    "Resource": "arn:aws:s3:::*",
                    "Effect": "Allow",
                    "Sid": "AllowS3ListAndLocationPermissions",
                },
                {
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:GetEncryptionConfiguration",
                        "s3:ListBucket",
                        "s3:DeleteObject",
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket.bucket_name}",
                        f"arn:aws:s3:::{bucket.bucket_name}/*",
                        f"arn:aws:s3:::aws-logs-{self.account}-{self.region}/elasticmapreduce/*",
                    ],
                    "Effect": "Allow",
                    "Sid": "AllowS3ReadOnlyAccessToLogs",
                },
            ],
        }
        custom_policy_document = iam.PolicyDocument.from_json(policy_document)
        studio_user_session_policy = iam.ManagedPolicy(self, "StudioUserSessionPolicy", document=custom_policy_document)

        # Set up Studio
        self.studio = emr.CfnStudio(
            self,
            f"{id}-EmrStudio",
            auth_mode="SSO",
            default_s3_location=f"s3://{bucket.bucket_name}/studio/",
            engine_security_group_id=eng_sg.security_group_id,
            name=f"{id}-EmrStudio",
            service_role=role.role_arn,
            subnet_ids=private_subnet_ids,
            user_role=user_role.role_arn,
            vpc_id=vpc_id,
            workspace_security_group_id=ws_sg.security_group_id,
            description=None,
            tags=None,
        )

        CfnOutput(self, id="StudioUrl", value=self.studio.attr_url)

        # Create session mapping
        emr.CfnStudioSessionMapping(
            self,
            f"{id}-StudioSM",
            identity_name=sso_username,
            identity_type="USER",
            session_policy_arn=studio_user_session_policy.managed_policy_arn,
            studio_id=self.studio.attr_studio_id,
        )

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())

        NagSuppressions.add_stack_suppressions(
            self,
            apply_to_nested_stacks=True,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Managed Policies are for service account roles only",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Resource access restriced to ADDF resources",
                },
            ],
        )

    def cert_gen(
        self,
        emailAddress="emailAddress",
        commonName="emroneks.com",
        countryName="NT",
        localityName="localityName",
        stateOrProvinceName="stateOrProvinceName",
        organizationName="organizationName",
        organizationUnitName="organizationUnitName",
        serialNumber=1234,
        validityStartInSeconds=0,
        validityEndInSeconds=10 * 365 * 24 * 60 * 60,
        KEY_FILE="private.key",
        CERT_FILE="selfsigned.crt",
    ):
        # create a key pair
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)
        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = countryName
        cert.get_subject().ST = stateOrProvinceName
        cert.get_subject().L = localityName
        cert.get_subject().O = organizationName  # noqa: E741
        cert.get_subject().OU = organizationUnitName
        cert.get_subject().CN = commonName
        cert.get_subject().emailAddress = emailAddress
        cert.set_serial_number(serialNumber)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(validityEndInSeconds)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, "sha512")
        return (crypto.dump_certificate(crypto.FILETYPE_PEM, cert), crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
