from aws_cdk import Aws, CfnOutput
from aws_cdk import aws_iam as iam
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class SMRoles(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        s3_bucket_prefix: str,
        env: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        cdk_deploy_policy = iam.Policy(
            self,
            "cdk_deploy_policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudformation:*",
                    ],
                    resources=["*"],  # TODO scope down
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["iam:PassRole"],
                    resources=[f"arn:aws:iam::{Aws.ACCOUNT_ID}:role/cdk*"],
                ),
            ],
        )
        sm_deny_policy = iam.Policy(
            self,
            "sm-deny-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    actions=[
                        "sagemaker:CreateProject",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    actions=["sagemaker:UpdateModelPackage"],
                    resources=["*"],
                ),
            ],
        )

        services_policy = iam.Policy(
            self,
            "services-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "lambda:Create*",
                        "lambda:Update*",
                        "lambda:Invoke*",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "sagemaker:ListTags",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "codecommit:GitPull",
                        "codecommit:GitPush",
                        "codecommit:*Branch*",
                        "codecommit:*PullRequest*",
                        "codecommit:*Commit*",
                        "codecommit:GetDifferences",
                        "codecommit:GetReferences",
                        "codecommit:GetRepository",
                        "codecommit:GetMerge*",
                        "codecommit:Merge*",
                        "codecommit:DescribeMergeConflicts",
                        "codecommit:*Comment*",
                        "codecommit:*File",
                        "codecommit:GetFolder",
                        "codecommit:GetBlob",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ecr:BatchGetImage",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:GetRepositoryPolicy",
                        "ecr:DescribeRepositories",
                        "ecr:DescribeImages",
                        "ecr:ListImages",
                        "ecr:GetAuthorizationToken",
                        "ecr:GetLifecyclePolicy",
                        "ecr:GetLifecyclePolicyPreview",
                        "ecr:ListTagsForResource",
                        "ecr:DescribeImageScanFindings",
                        "ecr:CreateRepository",
                        "ecr:CompleteLayerUpload",
                        "ecr:UploadLayerPart",
                        "ecr:InitiateLayerUpload",
                        "ecr:PutImage",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "servicecatalog:*",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "cloudformation:CreateStack",
                    ],
                    resources=["*"],
                ),
            ],
        )

        kms_policy = iam.Policy(
            self,
            "kms-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "kms:CreateGrant",
                        "kms:Decrypt",
                        "kms:DescribeKey",
                        "kms:Encrypt",
                        "kms:ReEncrypt",
                        "kms:GenerateDataKey",
                    ],
                    resources=["*"],
                ),
            ],
        )

        s3_policy = iam.Policy(
            self,
            "s3-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:AbortMultipartUpload",
                        "s3:DeleteObject",
                        "s3:Describe*",
                        "s3:GetObject",
                        "s3:PutBucket*",
                        "s3:PutObject",
                        "s3:PutObjectAcl",
                        "s3:GetBucketAcl",
                        "s3:GetBucketLocation",
                    ],
                    resources=[
                        "arn:aws:s3:::{}*/*".format(s3_bucket_prefix),
                        "arn:aws:s3:::{}*".format(s3_bucket_prefix),
                        "arn:aws:s3:::cdk*/*",
                        "arn:aws:s3:::cdk*",
                        "arn:aws:s3:::sagemaker*",
                        "arn:aws:s3:::sagemaker*/*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["s3:ListBucket"],
                    resources=[
                        "arn:aws:s3:::{}*".format(s3_bucket_prefix),
                        "arn:aws:s3:::cdk*",
                        "arn:aws:s3:::sagemaker*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    actions=["s3:DeleteBucket*"],
                    resources=["*"],
                ),
            ],
        )

        # create role for each persona

        # role for Data Scientist persona
        self.data_scientist_role = iam.Role(
            self,
            "data-scientist-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSLambda_ReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeCommitReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess",
                ),
            ],
        )

        sm_deny_policy.attach_to_role(self.data_scientist_role)
        services_policy.attach_to_role(self.data_scientist_role)
        kms_policy.attach_to_role(self.data_scientist_role)
        s3_policy.attach_to_role(self.data_scientist_role)

        ds_role_ssm_name = "/mlops/role/ds"
        ssm.StringParameter(
            self,
            "ssm-sg-ds-role",
            parameter_name=ds_role_ssm_name,
            string_value=self.data_scientist_role.role_arn,
        )
        CfnOutput(
            self,
            "DataScientistRoleSSMName",
            value=ds_role_ssm_name,
        )

        # role for Lead Data Scientist persona
        self.lead_data_scientist_role = iam.Role(
            self,
            "lead-data-scientist-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSLambda_ReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeCommitReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSCodeCommitPowerUser",
                ),
            ],
        )

        services_policy.attach_to_role(self.lead_data_scientist_role)
        kms_policy.attach_to_role(self.lead_data_scientist_role)
        s3_policy.attach_to_role(self.lead_data_scientist_role)
        cdk_deploy_policy.attach_to_role(self.lead_data_scientist_role)

        lead_ds_role_ssm_name = "/mlops/role/lead"
        ssm.StringParameter(
            self,
            "ssm-sg-lead-role",
            parameter_name=lead_ds_role_ssm_name,
            string_value=self.lead_data_scientist_role.role_arn,
        )
        CfnOutput(
            self,
            "LeadDataScientistRoleSSMName",
            value=lead_ds_role_ssm_name,
        )

        # default role for sagemaker persona
        self.sagemaker_studio_role = iam.Role(
            self,
            "sagemaker-studio-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("lambda.amazonaws.com"),
                iam.ServicePrincipal("sagemaker.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSLambda_ReadOnlyAccess",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSCodeCommitReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly",
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSageMakerFullAccess",
                ),
            ],
        )

        services_policy.attach_to_role(self.sagemaker_studio_role)
        kms_policy.attach_to_role(self.sagemaker_studio_role)
        s3_policy.attach_to_role(self.sagemaker_studio_role)

        sagemaker_execution_role_SSM_name = "/mlops/role/execution"
        ssm.StringParameter(
            self,
            "ssm-sg-execution-role",
            parameter_name=sagemaker_execution_role_SSM_name,
            string_value=self.sagemaker_studio_role.role_arn,
        )
        CfnOutput(
            self,
            "SageMakerExecutionRoleSSMName",
            value=sagemaker_execution_role_SSM_name,
        )
        CfnOutput(
            self,
            "SageMakerExecutionRoleArn",
            value=self.sagemaker_studio_role.role_arn,
        )
