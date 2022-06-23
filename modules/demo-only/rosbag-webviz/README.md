## Introduction

# Deploy and Visualize ROS Bag Data on AWS using Webviz for Autonomous Driving

In the automotive industry, ROS bag files are frequently used to capture drive data from test vehicles configured with cameras, LIDAR, GPS, and other input devices. The data for each device is stored as a topic in the ROS bag file. Developers and engineers need to visualize and inspect the contents of ROS bag files to identify issues or replay the drive data.

There are a couple of challenges to be addressed by migrating the visualization workflow into Amazon Web Services (AWS):

- Search, identify, and stream scenarios for ADAS engineers. Visualization tool should be ready instantly, load the data for a certain scenario over a search API, and show the first result through data streaming, to provide a good user experience.
- Native integration with the tool chain. Many customers implement the Data Catalog, data storage, and search API in AWS native services. This visualization tool should be integrated into such a tool chain directly.

This readme describes a solution on how to deploy and visualize ROS bag data on AWS by using webviz

**Webviz** is an open-source tool created by Cruise (https://getcruise.com/) that provides modular and configurable browser-based visualization.

In the autonomous driving data lake reference architecture (https://d1.awsstatic.com/architecture-diagrams/ArchitectureDiagrams/autonomous-driving-data-lake-ra.pdf?did=wp_card&trk=wp_card), the webviz visualization tool is covered in the step 10(picture below): Provide an advanced analytics and visualization toolchain including search function for particular scenarios using AWS AppSync, Amazon QuickSight (KPI reporting and monitoring), and Webviz, rviz, or other tooling for visualization.

### Recording reuse

The Industry Kit Program team reports on the impact that industry kits have for the AWS field and our customers. Please don't forget to record reuse for every customer you show this to.

In order to do so, click the "Record project reuse" button on this kit’s BuilderSpace page and enter the SFDC opportunity ID or paste the link to your SFDC opportunity.

![reuse](/assets/reuse.png)

## Support

If you notice a defect, or need support with deployment or demonstrating the kit, create an Issue here: [https://gitlab.aws.dev/industry-kits/automotive/autonomous-vehicle-datalake/-/issues]

## Prerequisities

Confirm you have followed the guide for working with the AWS CDK in TypeScript. (https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-typescript.html)

Install the AWS Command Line Interface (AWS CLI) v2 (https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)

Configure the AWS CLI. (https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)

## Architecture

![](/assets/mod4-arch.png)

## Deployment

### Input Paramenters

#### Required

- `target-bucket-name`: name of the Bucket configured to host ROS bag files when not using files with metadata in DynamoDB
- `raw-bucket-name`: name of the Bucket configured to host ROS bag files when using files with metadata in DynamoDB
- `vpd-id`: VPC to deploy the ALB into
- `scene-metadata-table-name`: DDB table with Metadata about ROS bag files
- `scene-metadata-partition-key`: DDB table partition key
- `scene-metadata-sort-key`: DDB table sort key

### Module Metadata Outputs

- `TargetBucketName`: Bucket configured to host ROS bag files
- `CorsLambdaName`: Lambda function to execute to get CORS url
- `GenerateUrlLambdaName`: Lambda function to generate visualization url
- `WebvizUrl`: URL of the ALB pointed to webviz
- `DemoUrl`: URL of the Private RestApi which invokes the GenerateUrl Lambda Function

#### Output Example

```json
{
  "TargetBucketName": "",
  "CorsLambdaName": "",
  "GenerateUrlLambdaName": "",
  "WebvizUrl": "",
  "DemoUrl": ""
}
```

### Upload ROS bag files

You can use the AWS CLI to copy a local bag file (from the assets folder in the cloned repo. The bag file that is [here](https://autonomous-datalake.s3.amazonaws.com/test_file_2GB.bag)]) to the specified S3 bucket using the aws s3 cp command. You can also copy files between S3 buckets with the aws s3 cp command.

### Generate streaming URL with helper script

The code repository contains a Python helper script in the project root to invoke your deployed Lambda function `generate_ros_streaming_url` locally with the correct payload. Please see below

You could leverage `ADDF` functionality to query the webviz CLoudFormation stack's output metadata by running:

```bash
$ export AWS_DEFAULTREGION=<AWS_REGION>
$ seedfarmer list moduledata -d <DEPLOYMENT_NAME> -g <GROUP_NAME> -m <MODULE_NAME>
```

> `AWS_DEFAULTREGION`: Set it to your current deployed region
> `DEPLOYMENT_NAME`: Your current deployment name. Eg: local or dev or prod
> `GROUP_NAME`: The group name under which the module is grouped under
> `MODULE_NAME`: The module name which is `rosbag-webviz`

Sample output from the above command looks like:

```yaml
{
  "CorsLambdaName": "addf-local-blogs-rosbag-webviz-cors-lambda",
  "GenerateUrlLambdaName": "addf-local-blogs-rosbag-webviz-generate-ros-streaming-url",
  "TargetBucketName": "addf-local-intermediate-bucket-us-west-2-XXXXXXXX",
  "WebvizUrl": "http://addf-local-blogs-rosbag-webviz-XXXXXXX.us-west-2.elb.amazonaws.com",
  "DemoUrl": "https://XXXXXXX.execute-api.us-west-2.amazonaws.com/get-url?",
}
```

A helper script is provided to demonstrate using the Lambda Function to generate a Webviz URL. The script requires as input the `TargetBucketName` and `GenerateUrlLambdaName` produced as metadata when the module is deployed. The `seedfarmer` utility provides utilities for reading this metadata and programmatically using it.

To run the helper script and manually provide the required inputs (make sure boto3 is installed or use pip install boto3 to install it):

> You can run the helper script on your local laptop or you can upload the script and test rosbag file to the `TargetBucketName` and query from the JupyterHub environment deployed on EKS.

```bash
$ python get_url.py \
  --bucket-name <VALUE OF "TargetBucketName" from the above output > \
  --function-name <VALUE OF "GenerateUrlLambdaName" from the above output > \
  --key <ros_bag_key>
```

To use the `seedfarmer` utility to query and store the metedata values from the deployed module you can (replace the `deployment`, `group`, and `module` names with values from you manifests):

```bash
$ seedfarmer list moduledata --deployment dev --group blogs --module rosbag-webviz > metadata.json
$ python get_url.py \
  --config-file metadata.json \
  --key <ros_bag_key> \
```

Alternatively, you can directly query and pipe the metadata to the `get_url.py` utility:

```bash
$ seedfarmer list moduledata --deployment dev --group blogs --module rosbag-webviz | \
  python get_url.py \
  --config-file - \
  --key <ros_bag_key>
```

> Optionally, you could provide `record_id` and `scene_id` to the above script invocation by calling `--record-id` and `--scene-id`
> Response format: http://webviz-lb-%3Caccount%3E.%3Cregion%3E.elb.amazonaws.com/?remote-bag-url=%3Cpresigned-url%3E

The response URL can be opened directly in your browser to visualize your targeted ROS bag file.

- Custom layouts for Webviz can be imported through json configs. This custom layout contains the topic configurations and window layouts specific to our ROS bag format and should be modified according to your ROS bag topics. Please see below.

  1. Select Config → Import/Export Layout
  2. Copy and paste the contents of layout.json

  ![](/assets/mod5-dep3.jpg)

- Alternatively, you can generate a streaming URL through Lambda function in the AWS Console
  You can generate a streaming URL by invoking your Lambda function generate_ros_streaming_url with the following example payload in the AWS console.

```json
{
  "key": "<ros_bag_key>",
  "bucket": "<bucket_name>",
  "seek_to": "<ros_timestamp>"
}
```

The seek_to value informs the Lambda function to add a parameter to jump to the specified ROS timestamp when generating the streaming URL.

Example output:

```json
{
  "statusCode": 200,
  "body": "{\"url\": \"http://webviz-lb-<domain>.<region>.elb.amazonaws.com?remote-bag-url=<PRESIGNED_ENCODED_URL>&seek-to=<ros_timestamp>\"}"
}
```

This body output URL can be opened in your browser to start visualizing your bag files directly.

By using a Lambda function to generate the streaming URL, you have the flexibility to integrate it with other user interfaces or dashboards. For example, if you use Amazon QuickSight to visualize different detected scenarios, you can define a customer action to invoke the Lambda function through API Gateway to get a streaming URL for the target scenario.

Similarly, custom web applications can be used to visualize the scenes and their corresponding ROS bag files stored in a metadata store. Invoke the Lambda function from your web server to generate and return a visualization URL that can be use by the web application.

## Testing and inspecting results

Open the streaming URL in your browser. If you added a seek_to value while generating the URL, it should jump to that point in the bag file.

### Using the streaming URL

Open the streaming URL in your browser. If you added a seek_to value while generating the URL, it should jump to that point in the bag file.

![](/assets/mod5-test1.jpg)

That’s it. You should now start to see your ROS bag file being streamed directly from Amazon S3 in your browser.

### Optional testing

If this Webviz solution is deployed in conjunction with [Module 1-Building an automated scene detection pipeline for Autonomous Driving – ADAS Workflow (ASD)](../analysis/rosbag-scene-detection/) it supports some out-of-the-box integration with webviz visualization.

You can configure the solution’s cdk.json to specify the relevant values for the SceneDescription table created by the ASD CDK code. Redeploy the stack after changing this using $ cdk deploy.

With these values, the Lambda function generate_ros_streaming_url now supports an additional payload format:

```json
{
"record_id": “<scene_description_table_partition_key>”,
"scene_id": “<scene_description_table_sort_key>”
}
```

The get_url.py script also supports the additional scene lookup parameters. To look up a scene stored in your SceneDescription table run the following commands in your terminal:

```bash
$ python get_url.py \
 –-record <scene_description_table_partition_key> \
 --scene <scene_description_table_sort_key>
```

Invoking the generate_ros_streaming_url with the record and scene parameters will result in a lookup of the ROS bag file for the scene from DynamoDB, presigning the ROS bag file and returning an URL to stream the file directly in your browser.

## Clean Up

To clean up the AWS RoboMaker development environment, review Deleting an Environment.

For the CDK application, you can destroy your CDK stack by running $ cdk destroy from your terminal. Some buckets will need to be manually emptied and deleted from the AWS console.

## Conclusion

This readme illustrated how to deploy a common tool to visualize ROS bag files. We showed you how to deploy Webviz on Fargate and configure a bucket to allow streaming bag files. Finally, you learned how streaming URLs can be generated and integrated into your custom scenario detection and visualization tools.

We hope you found this post interesting and helpful in extending your autonomous vehicle solutions, and invite your comments and feedback.

### Deployment Video (optional)

### Deployment FAQ (optional)
