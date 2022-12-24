from aws_cdk import aws_emrserverless as emrserverless
from aws_cdk import aws_iam as iam
from aws_cdk import Aspects, Stack, Tags, Duration
from constructs import Construct

class EmrServerlessStack(Stack):

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        deployment: str,
        module: str,
        **kwargs
        ) -> None:
            
        super().__init__(scope, construct_id, **kwargs)
        dep_mod = f"addf-{deployment}-{module}"
        dep_mod = dep_mod[:27]

        self.emr_app = emrserverless.CfnApplication (self, 
        f"{dep_mod}-emr-app",
        release_label="emr-6.8.0",
        type="Spark",
        auto_start_configuration=
        emrserverless.CfnApplication.AutoStartConfigurationProperty(
            enabled=True
        ),
        auto_stop_configuration
        =emrserverless.CfnApplication.AutoStopConfigurationProperty(
            enabled=False,
            idle_timeout_minutes=5
        ),
        initial_capacity=
        [emrserverless.CfnApplication.InitialCapacityConfigKeyValuePairProperty(
            key="Driver",
            value=emrserverless.CfnApplication.InitialCapacityConfigProperty(
                worker_configuration
                =emrserverless.CfnApplication.WorkerConfigurationProperty(
                    cpu="2vCPU",
                    memory="4GB",
    
                    # the properties below are optional
                    disk="20GB"
                ),
                worker_count=2
            )
        ),
        emrserverless.CfnApplication.InitialCapacityConfigKeyValuePairProperty(
            key="Executor",
            value=emrserverless.CfnApplication.InitialCapacityConfigProperty(
                worker_configuration
                =emrserverless.CfnApplication.WorkerConfigurationProperty(
                    cpu="2vCPU",
                    memory="4GB",
    
                    # the properties below are optional
                    disk="20GB"
                ),
                worker_count=4
            )
        )
        ],
        maximum_capacity
        =emrserverless.CfnApplication.MaximumAllowedResourcesProperty(
            cpu="100vCPU",
            memory="100GB",
    
            # the properties below are optional
            disk="1000GB"
        ),
        name=dep_mod
        )
        
        policy_statements = [
            iam.PolicyStatement(
                actions=["dynamodb:*"],
                effect=iam.Effect.ALLOW,
                resources=[f"arn:aws:dynamodb:{self.region}:{self.account}:table/addf*"],
            ),
            iam.PolicyStatement(
                actions=["s3:*"],
                effect=iam.Effect.ALLOW,
                resources=["arn:aws:s3:::addf-*", "arn:aws:s3:::addf-*/*"],
            ),
        ]
        iam_policy = iam.PolicyDocument(statements=policy_statements)

        self.job_role = iam.Role(
            self,
            f"{dep_mod}-emr-job-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("emr-serverless.amazonaws.com"),
            ),
            inline_policies={"DagPolicyDocument": iam_policy},
            max_session_duration=Duration.hours(12)
            )
    