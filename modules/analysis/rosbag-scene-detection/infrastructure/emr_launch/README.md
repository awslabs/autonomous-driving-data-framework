
## cluster_definition.py
    To be updated or extended if an EMR cluster requires additional permissions or configurations
    
    EMRClusterDefinition
        CDK Stack to define a Standard EMR Cluster
 
    EMRClusterDefinition.emr_resource_config()
        # Everything related to cluster sizing and hardware/software configuration. For example:
        
             master_instance_type: Optional[str] = 'm5.2xlarge',
             master_instance_market: Optional[InstanceMarketType] = InstanceMarketType.ON_DEMAND,
             core_instance_type: Optional[str] = 'm5.xlarge',
             core_instance_market: Optional[InstanceMarketType] = InstanceMarketType.ON_DEMAND,
             core_instance_count: Optional[int] = 2,
             applications: Optional[List[str]] = None,
             bootstrap_actions: Optional[List[emr_code.EMRBootstrapAction]] = None,
             configurations: Optional[List[dict]] = None,
             use_glue_catalog: Optional[bool] = True,
             step_concurrency_level: Optional[int] = 1,
             description: Optional[str] = None,
             secret_configurations: Optional[Dict[str, secretsmanager.Secret]] = None):
    
    EMRClusterDefinition.security_profile_config()
        # Everything related to the cluster's security configuration. For example:
             vpc: Optional[ec2.Vpc] = None,
             artifacts_bucket: Optional[s3.Bucket] = None,
             artifacts_path: Optional[str] = None,
             logs_bucket: Optional[s3.Bucket] = None,
             logs_path: Optional[str] = 'elasticmapreduce/',
             mutable_instance_role: bool = True,
             mutable_security_groups: bool = True,
             description: Optional[str] = None) -> None:
 
       EMRClusterDefinition.launch_function_config()
            # Everything related to checking for running clusters and lauching new clusters. 
            To be extended if the default step function for launching a cluster does not meet your needs.
            For example, if you want to use a permanent cluster or transient cluster. Implement that here. 
            
            
## Development
This repository uses the [AWS CDK](https://aws.amazon.com/cdk/) and the Professional Services developed 
    **AWS EMR Launch** plugin for the CDK to define EMR Clusters and Step Functions. 

It is recommended that a Python3 `venv` be used for all CDK builds and deployments.

To get up and running quickly:

1. Install the [CDK CLI](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)
   ```bash
   npm install -g aws-cdk
   ```

2. Use your mechanism of choice to create and activate a Python3 `venv`:
   ```bash
   python3 -m venv ~/.env
   source ~/.env/bin/activate
   ```

3. Install the CDK and Boto3 minimum requirements:
   ```bash
   pip install -r requirements.txt
   ```


    