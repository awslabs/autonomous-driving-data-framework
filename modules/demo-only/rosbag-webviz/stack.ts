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

import * as cdk from "aws-cdk-lib";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as cr from "aws-cdk-lib/custom-resources";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as dynamo from "aws-cdk-lib/aws-dynamodb";
import * as path from "path";
import * as apig from "aws-cdk-lib/aws-apigateway";
import { ApplicationLoadBalancedFargateService } from "aws-cdk-lib/aws-ecs-patterns";
import { RegionInfo } from "aws-cdk-lib/region-info";
import * as constructs from "constructs";

import {
  addCfnSuppressRules,
  addCfnSuppressToChildren,
  Rules,
} from "./helpers";
import { createAlbLoggingBucket, DefaultLoggingBucketProps } from "./utils";
import { LambdaIntegration } from "aws-cdk-lib/aws-apigateway";
import { ISubnet } from "aws-cdk-lib/aws-ec2";

interface WebvizStackProps extends cdk.StackProps {
  deploymentName?: string;
  moduleName?: string;
  targetBucketName?: string;
  rawBucketName?: string;
  logsBucketName?: string;
  vpcId?: string;
  privateSubnetIds?: string[];
  sceneMetadataTableName?: string;
  sceneMetadataPartitionKey?: string;
  sceneMetadataSortKey?: string;
  stageName?: string;
}

export class WebvizStack extends cdk.Stack {
  restApi: apig.RestApi;
  targetBucket: s3.IBucket;
  rawBucket: s3.IBucket;
  corsLambda: lambda.Function | undefined;
  corsProvider: cr.Provider | undefined;
  generateUrlLambda: lambda.Function | undefined;
  webvizUrl: string | undefined;
  privateSubnetIds: ISubnet[] | undefined;

  private getSubnetSelectionFromIds(subnetIds: string[]): ec2.SubnetSelection {
    return {
      subnets: subnetIds.map((subnetId) =>
        ec2.Subnet.fromSubnetId(this, subnetId, subnetId)
      ),
    };
  }

  constructor(
    scope: constructs.Construct,
    id: string,
    props: WebvizStackProps
  ) {
    super(scope, id, props);
    const region = this.region;
    const account = this.account;
    const elbname = `addf-${props.deploymentName}-${props.moduleName}`;

    const vpc = ec2.Vpc.fromLookup(this, "webviz-vpc", { vpcId: props.vpcId });

    let privateSubnetIds = this.getSubnetSelectionFromIds(
      props.privateSubnetIds as string[]
    );

    const appService = new ApplicationLoadBalancedFargateService(
      this,
      "webviz-alb-ecs-service",
      {
        loadBalancerName: elbname.substring(0, 30).concat("1"),
        taskImageOptions: {
          image: ecs.ContainerImage.fromRegistry("cruise/webviz"),
          containerPort: 8080,
        },
        vpc,
      }
    );

    this.webvizUrl = `http://${appService.loadBalancer.loadBalancerDnsName}`;

    this.targetBucket = s3.Bucket.fromBucketName(
      this,
      "bucketRef",
      props.targetBucketName!
    );

    this.rawBucket = s3.Bucket.fromBucketName(
      this,
      "rawbucketRef",
      props.rawBucketName!
    );

    this.corsLambda = new lambda.Function(this, "corsLambda", {
      code: lambda.Code.fromAsset(path.join(__dirname, "lambda", "put_cors")),
      functionName: `addf-${props.deploymentName}-${props.moduleName}-cors-lambda`,
      handler: "main.lambda_handler",
      runtime: lambda.Runtime.PYTHON_3_8,
      reservedConcurrentExecutions: 1,
      role: new iam.Role(this, "lambdaPutCorsRulesRole", {
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName(
            "service-role/AWSLambdaBasicExecutionRole"
          ),
        ],
        assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
        inlinePolicies: {
          "allow-put-cors": new iam.PolicyDocument({
            statements: [
              new iam.PolicyStatement({
                actions: ["s3:PutBucketCORS"],
                resources: [
                  this.targetBucket.bucketArn,
                  this.rawBucket.bucketArn,
                ],
                effect: iam.Effect.ALLOW,
              }),
            ],
          }),
        },
      }),
    });

    this.corsProvider = new cr.Provider(this, "corsCustomProvider", {
      vpc: vpc,
      vpcSubnets: privateSubnetIds,
      onEventHandler: this.corsLambda,
    });

    new cdk.CustomResource(this, "putCorsRulesCustomResource", {
      serviceToken: this.corsProvider.serviceToken,
      properties: {
        bucket_name: this.targetBucket.bucketName,
        raw_bucket_name: this.rawBucket.bucketName,
        allowed_origin: this.webvizUrl,
      },
    });

    const generateUrlLambdaRole = new iam.Role(this, "generateUrlLambdaRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole"
        ),
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaVPCAccessExecutionRole"
        ),
      ],
    });

    this.targetBucket.grantRead(generateUrlLambdaRole);
    this.rawBucket.grantRead(generateUrlLambdaRole);

    let lambdaEnvs: any = {};
    (lambdaEnvs["SCENE_DB_PARTITION_KEY"] = props.sceneMetadataPartitionKey),
      (lambdaEnvs["SCENE_DB_SORT_KEY"] = props.sceneMetadataSortKey),
      (lambdaEnvs["SCENE_DB_REGION"] = this.region),
      (lambdaEnvs["SCENE_DB_TABLE"] = props.sceneMetadataTableName);

    const dynamoDb = dynamo.Table.fromTableName(
      this,
      "scenario-table-ref",
      props.sceneMetadataTableName!
    );
    dynamoDb.grantReadWriteData(generateUrlLambdaRole);

    const endpointSG = new ec2.SecurityGroup(this, "endpointSecurityGroup", {
      vpc,
      allowAllOutbound: true,
      securityGroupName: `addf-${props.deploymentName}-${props.moduleName}-apig-endpoint`,
    });

    const vpcEndpoint = new ec2.InterfaceVpcEndpoint(
      this,
      "restApiVpcEndpoint",
      {
        vpc,
        service: {
          name: `com.amazonaws.${region}.execute-api`,
          port: 443,
        },
        subnets:
          props.privateSubnetIds === undefined ? undefined : privateSubnetIds,
        privateDnsEnabled: true,
        securityGroups: [endpointSG],
      }
    );

    const generateUrlLambdaName = `addf-${props.deploymentName}-${props.moduleName}-generate-ros-streaming-url`;
    this.generateUrlLambda = new lambda.Function(this, "generateUrlLambda", {
      code: lambda.Code.fromAsset(
        path.join(__dirname, "lambda", "generate_url")
      ),
      handler: "main.lambda_handler",
      functionName:
        generateUrlLambdaName.length > 64
          ? generateUrlLambdaName.substring(0, 64)
          : generateUrlLambdaName,
      runtime: lambda.Runtime.PYTHON_3_8,
      reservedConcurrentExecutions: 1,
      environment: {
        WEBVIZ_ELB_URL: this.webvizUrl,
        ...lambdaEnvs,
      },
      role: generateUrlLambdaRole,
    });

    this.generateUrlLambda.addToRolePolicy(
      new iam.PolicyStatement({
        sid: "CloudAuthAPIGatewayInvokeFullAccess",
        effect: iam.Effect.ALLOW,
        actions: ["execute-api:Invoke"],
        resources: [`arn:aws:execute-api:*:${account}:*`],
      })
    );

    this.restApi = new apig.RestApi(this, "generateUrlRestAPI", {
      restApiName: `addf-${props.deploymentName}-${props.moduleName}-demo-webviz`,
      description: "API to abstract the Generate URL Lambda",
      endpointTypes: [apig.EndpointType.PRIVATE],
      policy: new iam.PolicyDocument({
        statements: [
          new iam.PolicyStatement({
            principals: [new iam.AnyPrincipal()],
            actions: ["execute-api:Invoke"],
            resources: ["execute-api:/*"],
            effect: iam.Effect.DENY,
            conditions: {
              StringNotEquals: {
                "aws:SourceVpce": vpcEndpoint.vpcEndpointId,
              },
            },
          }),
          new iam.PolicyStatement({
            principals: [new iam.AnyPrincipal()],
            actions: ["execute-api:Invoke"],
            resources: ["execute-api:/*"],
            effect: iam.Effect.ALLOW,
          }),
        ],
      }),
      deployOptions: {
        stageName: props.stageName,
        metricsEnabled: true,
        loggingLevel: apig.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
      },
    });

    const requestTemplate = {
      record_id: "$input.params().querystring['record_id']",
      scene_id: "$input.params().querystring['scene_id']",
      bucket: "$input.params().querystring['bucket']",
      key: "$input.params().querystring['key']",
      seek_to: "$input.params().querystring['seek_to']",
    };

    const integrationResponse: apig.IntegrationResponse = {
      statusCode: "200",
      contentHandling: apig.ContentHandling.CONVERT_TO_TEXT,
    };

    const methodResponse: apig.MethodResponse = {
      statusCode: "200",
      responseModels: { "application/json": apig.Model.EMPTY_MODEL },
    };

    const integration = new LambdaIntegration(this.generateUrlLambda, {
      allowTestInvoke: true,
      proxy: false,
      integrationResponses: [integrationResponse],
      passthroughBehavior: apig.PassthroughBehavior.WHEN_NO_TEMPLATES,
      requestTemplates: { "application/json": JSON.stringify(requestTemplate) },
    });

    this.restApi.root.addMethod("GET", integration, {
      methodResponses: [methodResponse],
      requestParameters: {
        "method.request.querystring.record_id": false,
        "method.request.querystring.scene_id": false,
        "method.request.querystring.bucket": false,
        "method.request.querystring.key": false,
        "method.request.querystring.seek_to": false,
      },
    });

    // Confirmed that the Bucket Policy on an imported bucket can't be updated with permissions required to
    // enable the loadbalancer S3 logs. Bucket will either need to be created by this Stack or Bucket Policy
    // has to manually updated before deploying the Stack

    // const loggingBucket = s3.Bucket.fromBucketName(this, 'loadbalancerLogsBucket', props.logsBucketName!)
    // const prefix = `addf-${props.deploymentName}-${props.moduleName}`
    // if (cdk.Token.isUnresolved(region)) {
    //     throw new Error('Region is required to enable ELBv2 access logging')
    // }

    // const account = RegionInfo.get(region).elbv2Account;
    // if (!account) {
    //     throw new Error(`Cannot enable access logging; don't know ELBv2 account for region ${region}`)
    // }

    // const logsDeliveryServicePrincipal = new iam.ServicePrincipal('delivery.logs.amazonaws.com')
    // loggingBucket.grantPut(new iam.AccountPrincipal(account), `${(prefix ? prefix + '/' : '')}AWSLogs/${this.account}/*`)
    // loggingBucket.addToResourcePolicy(
    //     new iam.PolicyStatement({
    //         actions: ['s3:PutObject'],
    //         principals: [logsDeliveryServicePrincipal],
    //         resources: [
    //             loggingBucket.arnForObjects(`${prefix ? prefix + '/' : ''}AWSLogs/${this.account}/*`),
    //         ],
    //         conditions: {
    //             StringEquals: { 's3:x-amz-acl': 'bucket-owner-full-control' },
    //         },
    //     }),
    // )
    // loggingBucket.addToResourcePolicy(
    //     new iam.PolicyStatement({
    //         actions: ['s3:GetBucketAcl'],
    //         principals: [logsDeliveryServicePrincipal],
    //         resources: [loggingBucket.bucketArn],
    //     }),
    // )
    // appService.loadBalancer.logAccessLogs(loggingBucket, prefix)

    // const loggingBucket = createAlbLoggingBucket(
    //     this, "loadbalancer-logs", DefaultLoggingBucketProps(
    //         `addf-${props.deploymentName}-${props.moduleName}-${this.region}-${this.account}`
    //     ), this.account)
    // appService.loadBalancer.logAccessLogs(loggingBucket)

    /* CFN Nag Supressions */
    addCfnSuppressRules(this.generateUrlLambda, [Rules.W58_VIA_MANAGED_POLICY]);
    addCfnSuppressRules(appService.listener, [Rules.W56_OUT_OF_SCOPE]);
    addCfnSuppressRules(appService.loadBalancer, [
      Rules.W28_CDK_AUTO_GEN_PATTERNS,
    ]);
    addCfnSuppressRules(appService.service, [Rules.W86_CDK_AUTO_GEN_PATTERNS]);
    addCfnSuppressToChildren(
      appService,
      [Rules.W2_PUBLIC_FACING_LB, Rules.W9_PUBLIC_FACING_LB],
      "AWS::EC2::SecurityGroup"
    );
    addCfnSuppressToChildren(
      this,
      [Rules.W5_CDK_AUTO_GEN_SGS, Rules.W40_CDK_AUTO_GEN_SGS],
      "AWS::EC2::SecurityGroup"
    );
    addCfnSuppressToChildren(
      this,
      [Rules.W92_CDK_AUTO_GEN_LAMBDA_FUNC, Rules.W89_CDK_AUTO_GEN_LAMBDA_FUNC],
      "AWS::Lambda::Function"
    );
    if (this.corsLambda) {
      addCfnSuppressRules(this.corsLambda, [Rules.W58_VIA_MANAGED_POLICY]);
    }

    if (this.corsProvider) {
      addCfnSuppressToChildren(
        this.corsProvider,
        [Rules.W58_CDK_AUTO_GEN_CUSTOM_PROVIDER],
        "AWS::Lambda::Function"
      );
    }
  }
}
