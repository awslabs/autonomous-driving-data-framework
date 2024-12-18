// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

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
  process.env.ADDF_PARAMETER_PRIVATE_SUBNET_IDS as string,
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
  description:
    "(SO9154) Autonomous Driving Data Framework (ADDF) - Visualization",
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
