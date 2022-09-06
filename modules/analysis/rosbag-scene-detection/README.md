## Introduction
# Building an automated scene detection pipeline for Autonomous Driving – ADAS Workflow
Many organizations face the challenge of ingesting, transforming, labeling, and cataloging massive amounts of data to develop automated driving systems. In this module, we explored an architecture to solve this problem using Amazon EMR, Amazon S3, Amazon SageMaker Ground Truth, and more. 

### Recording reuse

The Industry Kit Program team reports on the impact that industry kits have for the AWS field and our customers. Don't forget to record reuse for every customer you show this to.

In order to do so, click the "Record project reuse" button on this kit’s BuilderSpace page and enter the SFDC opportunity ID or paste the link to your SFDC opportunity.

![reuse](/assets/reuse.png)

## Support

If you notice a defect, or need support with deployment or demonstrating the kit, create an Issue here: [https://gitlab.aws.dev/industry-kits/automotive/autonomous-vehicle-datalake/-/issues]

## Prerequisities

* This post uses an AWS Cloud Development Kit (CDK) stack written in Python. You should follow the instructions in the AWS CDK Getting Started guide to set up your environment so you are ready to begin.

* You can use the `config.json` available within the module to declare the parameters which are standard to the entire module irrespective of the deployment(s).   
> Example: to customize the ROS bag topics to be extracted   

* You can use the manifest file for the `rosbag-scene-detection` module available within the manifests directory `manifests/ENVIRONMENT_TYPE/blog-modules.yaml`  to declare the parameters which should change for every deployment.   
> Example: to set the sizing of your EMR cluster  

#### Required Parameters which should be configured in the `manifests/ENVIRONMENT_TYPE/blog-modules.yaml`

- `vpc-id`: VPC Id to be used by the Scene Detection resources
- `private-subnet-ids`: List of Private Subnets Ids where the Scene Detection resources should be deployed to
- `source-bucket-name`: Source Bucket to which the rosbag files should be uploaded to
- `destination-bucket-name`: Intermediate Bucket to which the parsed data will be uploaded to
- `artifact-bucket-name`: The Artifact bucket to which Scene Detection pipeline can upload any assets, other than module specific data
- `logs-bucket-name`: The logs bucket to which the Scene Detection resources can write their infrastructure logs to
- `glue-db-name`: The GlueDB to be used by the Scene Detection pipeline
- `rosbag-bagfile-table`: The DynamoDB to be used for writing rosbag file metadata
- `rosbag-scene-metadata-table`: The DynamoDB to be used for writing the rosbag scene metadata
- `emr`: The Cluster Configuration to be used for creating the EMR environment
- `fargate`: The Cluster Configuration/details to used for creating ECS Fargate environment


* You will also need to be authenticated into an AWS account with permissions to deploy resources before executing the deploy script.

* This kit works in any region where the deployed resources are available/supported.   

## Architecture

![](/assets/Architecture-for-Deploying-Autonomous-Driving-ADAS-workloads-at-scale-3.jpg)

## Deployment

- The ADDF CLI creates an ECR repository based on the input provided via the parameter `ecr-repository-name` in the blog-modules.yaml, if it doesnt exist

- Once the ECR repository is created in your account, the docker image is built and pushed to that repository.   

- Further, the pipeline will be deployed by executing the CDK command to deploy all infrastructure defined in `app.py` and the progress of the deployment can be followed on the command line, but also in the CloudFormation section of the AWS console.   

- Once deployed, the user must upload 2 or more bag files to the rosbag-ingest bucket to initiate the pipeline. In the rosbog-ingest bucket, create a folder called 'demo' and use the below two bag files. You must be connected to VPN to download these.
- [File 1 to upload to the rosbag-ingest bucket](https://s3.amazonaws.com/aws-autonomous-driving-datasets/test-vehicle-01/072021/small1__2020-11-19-16-21-22_4.bag). 
- [File 2 to upload to the rosbag-ingest bucket](https://s3.amazonaws.com/aws-autonomous-driving-datasets/test-vehicle-01/072021/small2__2020-11-19-16-21-22_4.bag).

- If you run into issues, please see FAQs at the botton of this readme file for more instructions on dpeloyment and troubleshooting.

## Solution Walkthrough and Testing:

## How to: ROS bag ingestion with ECS Tasks, Fargate, and EFS
This solution provides an end-to-end scene detection pipeline for ROS bag files, ingesting the ROS bag files from S3, and transforming the topic data to perform scene detection in PySpark on EMR. This then exposes scene descriptions via DynamoDB to downstream consumers.

The pipeline starts with an S3 bucket (as shown in the architecture diagram as #1) where incoming ROS bag files can be uploaded from local copy stations as needed. We recommend, using Amazon Direct Connect for a private, high-throughout connection to the cloud.

- This ingestion bucket is configured to initiate S3 notifications each time an object ending with “.bag” is created. An AWS Lambda function then initiates a Step Function for orchestrating the ECS Task. This passes the bucket and bag file prefix to the ECS task as environment variables in the container.

- The ECS Task (as shown in the architecture diagram as #2) runs serverless leveraging Fargate as the capacity provider, this avoids the need to provision and autoscale EC2 instances in the ECS cluster. 

- Each ECS Task processes exactly one bag file. We use Elastic FileStore to provide virtually unlimited file storage to the container, in order to easily work with larger bag files. The container uses the open-source bagpy python library to extract structured topic data (for example, GPS, detections, inertial measurement data,). 

- The topic data is uploaded as parquet files to S3, partitioned by topic and source bag file. The application writes metadata about each file, such as the topic names found in the file and the number of messages per topic, to a DynamoDB table (as shown in the architecture diagram as #4).

- This module deploys an AWS  Glue Crawler configured to crawl this bucket of topic parquet files. These files populate the AWS Glue Catalog with the schemas of each topic table and make this data accessible in Athena, Glue jobs, Quicksight, and Spark on EMR.  We use the AWS Glue Catalog (as shown in the architecture diagram as #5) as a permanent Hive Metastore.

- **Glue Data Catalog of parquet datasets on S3 is shown below:**

![](/assets/mod1-dep1.png)

- **To Run ad-hoc queries against the Glue tables using Amazon Athena, see picture below:**

![](/assets/mod1-dep2.png)

- The topic parquet bucket also has an S3 Notification configured for all newly created objects, which is consumed by an EMR-Trigger Lambda (as shown in the architecture diagram as #5). 

- This Lambda function is responsible for keeping track of bag files and their respective parquet files in DynamoDB (as shown in the architecture diagram as #6). Once in DynamoDB, bag files are assigned to batches, initiating the EMR batch processing step function. Metadata is stored about each batch including the step function execution ARN in DynamoDB.

- **EMR pipeline orchestration with AWS Step Functions is shown in the picture below:**

![](/assets/mod1-dep3.png)

- The EMR batch processing step function (as shown in the architecture diagram as #7) orchestrates the entire EMR pipeline, from provisioning an EMR cluster using the open-source EMR-Launch CDK library to submitting Pyspark steps to the cluster, to terminating the cluster and handling failures.

## Explanation of Batch Scene Analytics with Spark on EMR

- There are two PySpark applications running on our cluster. The first performs synchronization of ROS bag topics for each bagfile. As the various sensors in the vehicle have different frequencies, we synchronize the various frequencies to a uniform frequency of 1 signal per 100 ms per sensor. This makes it easier to work with the data.

- We compute the minimum and maximum timestamp in each bag file, and construct a unified timeline. For each 100 ms we take the most recent signal per sensor and assign it to the 100 ms timestamp. After this is performed, the data looks more like a normal relational table and is easier to query and analyze.

- **Batch Scene Analytics with Spark on EMR is shown below.**

![](/assets/mod1-dep4.png)

## Explanation of Scene Detection and Labeling in PySpark

- The second spark application enriches the synchronized topic dataset (as shown in the architecture diagram as #8), analyzing the detected lane points and the object detections. The goal is to perform a simple lane assignment algorithm for objects detected by the on-board ML models and to save this enriched dataset (as shown in the architecture diagram as #9) back to S3 for easy-access by analysts and data scientists.

- **Object Lane Assignment Example can be in the picture below:**

![](/assets/mod1-dep5.png)

- **Synchronized topics enriched with object lane assignments is shown in the picture below:**

![](/assets/mod1-dep6.png)

- Finally, the last step takes this enriched dataset (as shown in the architecture diagram as #9) to summarize specific scenes or sequences where a person was identified as being in a lane. The output of this pipeline includes two new tables as parquet files on S3 – the synchronized topic dataset (as shown in the architecture diagram as #8) and the synchronized topic dataset enriched with object lane assignments (as shown in the architecture diagram as #9), as well as a DynamoDB table with scene metadata for all person-in-lane scenarios (as shown in the architecture diagram as #10).

## Scene Metadata

- The Scene Metadata DynamoDB table (as shown in the architecture diagram as #10) can be queried directly to find sequences of events, as will be covered in a follow up post for visually debugging scene detection algorithms using WebViz/RViz. Using WebViz, we were able to detect that the on-board object detection model labels Crosswalks and Walking Signs as “person” even when a person is not crossing the street, for example:

- **Example of DynamoDB item from the Scene Metadata table are shown below:**

![](/assets/mod1-dep7.jpg)

![](/assets/mod1-dep8.png)

- These scene descriptions can also be converted to Open Scenario format and pushed to an ElasticSearch cluster to support more complex scenario-based searches. For example, downstream simulation use cases or for visualization in QuickSight. An example of syncing DynamoDB tables to ElasticSearch using DynamoDB streams and Lambda can be found here (https://aws.amazon.com/blogs/compute/indexing-amazon-dynamodb-content-with-amazon-elasticsearch-service-using-aws-lambda/). 

- As DynamoDB is a NoSQL data store, we can enrich the Scene Metadata table with scene parameters. For example, we can identify the maximum or minimum speed of the car during the identified event sequence, without worrying about breaking schema changes. It is also straightforward to save a dataframe from PySpark to DynamoDB using open-source libraries.

As a final note, the modules are built to be exactly that, modular. The three modules that are easily isolated are:

the ECS Task pipeline for extracting ROS bag topic data to parquet files

the EMR Trigger Lambda for tracking incoming files, creating batches, and initiating a batch processing step function

the EMR Pipeline for running PySpark applications leveraging Step Functions and EMR Launch

## Clean Up

To clean up the deployment, you can run bash deploy.sh destroy false. Some resources like S3 buckets and DynamoDB tables may have to be manually emptied and deleted via the console to be fully removed.

## Limitations

The bagpy library used in this pipeline does not yet support complex or non-structured data types like images or LIDAR data. Therefore its usage is limited to data that can be stored in a tabular csv format before being converted to parquet.

## **Conclusion**

In this module and readme, we showed how to build an end-to-end Scene Detection pipeline at scale on AWS to perform scene analytics and scenario detection with Spark on EMR from raw vehicle sensor data. In a subsequent blog post, we will cover how how to extract and catalog images from ROS bag files, create a labelling job with SageMaker GroundTruth and then train a Machine Learning Model to detect cars.

We hope you found this interesting and helpful and invite your comments on the solution!

## Troubleshooting and FAQs

- **How to customize input and add complex transformational logic?**

Edit the topics-to-extract list in the config.json:
These topics should all be in each rosbag file, as the emr pipeline will wait for all topics to arrive on s3 before processing the next batch
Extend the ./service/app/engine.py file to add more complex transformation logic

Customizing Input:
    Add prefix and suffix filters for the S3 notifications in config.json

- **What to do if automatic creation of the virtualenv fails?**

This project is set up like a standard Python project.  The initialization process also creates a virtualenv within this project, stored under the .env directory.  To create the virtualenv it assumes that there is a python3 (or python for Windows) executable in your path with access to the venv
package. If for any reason the automatic creation of the virtualenv fails,you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

$ python3 -m venv .env

After the init process completes and the virtualenv is created, you can use the following step to test deployment


$ bash deploy.sh deploy true

- **How to add additoinal dependencies such as cdk libraries etc.?**

To add additional dependencies, for example other CDK libraries, just add them to your requirements.txt or setup.py file and rerun the pip install -r requirements.txt command.

- **What to do when encountered with this error (Terminated with errors: The request to create the EMR cluster or add EC2 instances to it failed. )?**

The number of vCPUs for instance type m5.4xlarge exceeds the EC2 service quota for that type. Request a service quota increase for your AWS account or choose a different instance type and retry the request. For more information, see https://docs.aws.amazon.com/console/elasticmapreduce/vcpu-limit. You can ask for limit increase to 80.

- **What to do when encountered with this error - (Service-linked role 'AWSServiceRoleForEMRCleanup' for EMR is required. Please create this role directly or add permission to create it in your IAM entity)?**

Creating a service-linked role for Amazon EMR
You don't need to manually create the AWSServiceRoleForEMRCleanup role. When you launch a cluster, either for the first time or when a service-linked role is not present, Amazon EMR creates the service-linked role for you. You must have permissions to create the service-linked role. For an example statement that adds this capability to the permissions policy of an IAM entity (such as a user, group, or role), see Service-linked role permissions for Amazon EMR https://docs.aws.amazon.com/emr/latest/ManagementGuide/using-service-linked-roles.html#service-linked-role-permissions

- **What are the topics in VSI Rosbag Files Data?**
         /as_tx/objects                         197 msgs    : derived_object_msgs/ObjectWithCovarianceArray
         /flir_adk/rgb_front_left/image_raw     198 msgs    : sensor_msgs/Image                            
         /flir_adk/rgb_front_right/image_raw    197 msgs    : sensor_msgs/Image                            
         /flir_adk/thermal/image_raw            195 msgs    : sensor_msgs/Image                            
         /gps                                   980 msgs    : visualization_msgs/Marker                    
         /imu_raw                               986 msgs    : sensor_msgs/Imu                              
         /muncaster/rgb/detections_only         197 msgs    : fusion/image_detections                      
         /muncaster/thermal/detections_only     197 msgs    : fusion/image_detections                      
         /nira_log/tgi                          490 msgs    : nira_log/tgi                                 
         /os1_cloud_node/points                 197 msgs    : sensor_msgs/PointCloud2                      
         /rosout                                 15 msgs    : rosgraph_msgs/Log                             (2 connections)
         /vehicle/brake_info_report             493 msgs    : dbw_mkz_msgs/BrakeInfoReport                 
         /vehicle/brake_report                  493 msgs    : dbw_mkz_msgs/BrakeReport                     
         /vehicle/fuel_level_report              98 msgs    : dbw_mkz_msgs/FuelLevelReport                 
         /vehicle/gear_report                   197 msgs    : dbw_mkz_msgs/GearReport                      
         /vehicle/gps/fix                         9 msgs    : sensor_msgs/NavSatFix                        
         /vehicle/gps/time                        9 msgs    : sensor_msgs/TimeReference                    
         /vehicle/gps/vel                         9 msgs    : geometry_msgs/TwistStamped                   
         /vehicle/imu/data_raw                  986 msgs    : sensor_msgs/Imu                              
         /vehicle/joint_states                 1974 msgs    : sensor_msgs/JointState                       
         /vehicle/misc_1_report                 196 msgs    : dbw_mkz_msgs/Misc1Report                     
         /vehicle/sonar_cloud                    33 msgs    : sensor_msgs/PointCloud2                      
         /vehicle/steering_report               988 msgs    : dbw_mkz_msgs/SteeringReport                  
         /vehicle/surround_report                33 msgs    : dbw_mkz_msgs/SurroundReport                  
         /vehicle/throttle_info_report          980 msgs    : dbw_mkz_msgs/ThrottleInfoReport              
         /vehicle/throttle_report               492 msgs    : dbw_mkz_msgs/ThrottleReport                  
         /vehicle/tire_pressure_report           19 msgs    : dbw_mkz_msgs/TirePressureReport              
         /vehicle/twist                         988 msgs    : geometry_msgs/TwistStamped                   
         /vehicle/wheel_position_report         491 msgs    : dbw_mkz_msgs/WheelPositionReport             
         /vehicle/wheel_speed_report            981 msgs    : dbw_mkz_msgs/WheelSpeedReport


- What are some useful CDK commands?

bash deploy.sh ls false      -    list all stacks in the app

bash deploy.sh synth false    -   emits the synthesized CloudFormation template

bash deploy.sh deploy true   -   build and deploy this stack to your default AWS account/region

bash deploy.sh diff true    -    compare deployed stack with current state

bash deploy.sh docs false     -   open CDK documentation


### CFN Nag
cfn_nag_scan --input-path deployment/module1-scene-detection-emr-orchestration.yaml  --deny-list-path cfn-nag-suppress.txt


### Deployment Video (optional)

### Deployment FAQ (optional)
