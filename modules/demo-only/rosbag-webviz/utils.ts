import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";
// Note: To ensure CDKv2 compatibility, keep the import statement for Construct separate
import { Construct } from "constructs";
import { RemovalPolicy } from "aws-cdk-lib/core";
import { BucketProps } from "aws-cdk-lib/aws-s3";
import { PolicyStatement, Effect } from "aws-cdk-lib/aws-iam";

//import elb as elb from './index'
export function createAlbLoggingBucket(
  scope: Construct,
  bucketId: string,
  loggingBucketProps: s3.BucketProps,
  accountId: string
): s3.Bucket {
  // Create the Logging Bucket
  const loggingBucket: s3.Bucket = new s3.Bucket(
    scope,
    bucketId,
    loggingBucketProps
  );

  applySecureBucketPolicy(loggingBucket, accountId);

  return loggingBucket;
}

export function applySecureBucketPolicy(
  s3Bucket: s3.Bucket,
  accountId: string
): void {
  // Apply bucket policy to enforce encryption of data in transit
  s3Bucket.addToResourcePolicy(
    new PolicyStatement({
      sid: "HttpsOnly",
      resources: [s3Bucket.bucketArn + "/*"],
      actions: ["s3:Get*", "s3:List*", "s3:Put*"],
      principals: [new iam.AccountPrincipal(accountId)],
      effect: Effect.DENY,
      conditions: {
        Bool: {
          "aws:SecureTransport": "false",
        },
      },
    })
  );
}

export function DefaultLoggingBucketProps(bucketName: string): s3.BucketProps {
  return {
    bucketName,
    encryption: s3.BucketEncryption.S3_MANAGED,
    versioned: true,
    blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    removalPolicy: RemovalPolicy.RETAIN,
  } as BucketProps;
}
