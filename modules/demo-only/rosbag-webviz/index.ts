/*!
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { WebvizStack } from "./stack";

const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION;
const stageName = "get-url";
const deploymentName = process.env.ADDF_DEPLOYMENT_NAME;
const moduleName = process.env.ADDF_MODULE_NAME;

const targetBucketName = process.env.ADDF_PARAMETER_TARGET_BUCKET_NAME;
const rawBucketName = process.env.ADDF_PARAMETER_RAW_BUCKET_NAME;
const logsBucketName = process.env.ADDF_PARAMETER_LOGS_BUCKET_NAME;
const vpcId = process.env.ADDF_PARAMETER_VPC_ID;
const privateSubnetIds: string[] = JSON.parse(
  process.env.ADDF_PARAMETER_PRIVATE_SUBNET_IDS as string
);
const sceneMetadataTableName =
  process.env.ADDF_PARAMETER_SCENE_METADATA_TABLE_NAME;
const sceneMetadataPartitionKey =
  process.env.ADDF_PARAMETER_SCENE_METADATA_PARTITION_KEY;
const sceneMetadataSortKey = process.env.ADDF_PARAMETER_SCENE_METADATA_SORT_KEY;

const app = new cdk.App();

// This module can be deployed only once per ADDF Deployment
const stack = new WebvizStack(app, `addf-${deploymentName}-${moduleName}`, {
  deploymentName,
  moduleName,
  targetBucketName,
  rawBucketName,
  logsBucketName,
  vpcId,
  privateSubnetIds,
  sceneMetadataTableName,
  sceneMetadataPartitionKey,
  sceneMetadataSortKey,
  stageName,
  description: "This stack deploys Webviz resources for Visualization",
  env: { account, region },
});

new cdk.CfnOutput(stack, "metadata", {
  value: JSON.stringify({
    TargetBucketName: stack.targetBucket.bucketName,
    CorsLambdaName: stack.corsLambda?.functionName,
    GenerateUrlLambdaName: stack.generateUrlLambda?.functionName,
    WebvizUrl: stack.webvizUrl,
    DemoUrl: `https://${stack.restApi.restApiId}.execute-api.${region}.amazonaws.com/${stageName}?`,
  }),
});

app.synth();
