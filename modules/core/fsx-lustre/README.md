## Introduction
FSx on Lustre

## Description

This module creates FSx for Lustre

## Inputs/Outputs


### Input Parameters


#### Required
- `vpc_id`: The VPC in which to create the security group for your file system
- `private_subnet_ids`: Specifies the IDs of the subnets that the file system will be accessible from
- `fs_deployment_type`:
  - Choose `SCRATCH_1` and `SCRATCH_2` deployment types when you need temporary storage and shorter-term processing of data. The `SCRATCH_2` deployment type provides in-transit encryption of data and higher burst throughput capacity than `SCRATCH_1` .
  - Choose `PERSISTENT_1` for longer-term storage and for throughput-focused workloads that aren’t latency-sensitive. `PERSISTENT_1` supports encryption of data in transit, and is available in all AWS Regions in which FSx for Lustre is available.
  - Choose `PERSISTENT_2` for longer-term storage and for latency-sensitive workloads that require the highest levels of IOPS/throughput. `PERSISTENT_2` supports SSD storage, and offers higher PerUnitStorageThroughput (up to 1000 MB/s/TiB). `PERSISTENT_2` is available in a limited number of AWS Regions.
  - For more information, and an up-to-date list of AWS Regions in which `PERSISTENT_2` is available, see File system deployment options for FSx for Lustre in the Amazon FSx for Lustre User Guide . .. epigraph:: If you choose `PERSISTENT_2` , and you set FileSystemTypeVersion to 2.10, the CreateFileSystem operation fails. Encryption of data in transit is automatically turned on when you access SCRATCH_2 , PERSISTENT_1 and `PERSISTENT_2` file systems from Amazon EC2 instances that [support automatic encryption](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/data- protection.html) in the AWS Regions where they are available. For more information about encryption in transit for FSx for Lustre file systems, see Encrypting data in transit in the Amazon FSx for Lustre User Guide . (Default = SCRATCH_1 )

#### Optional
- `data_bucket_name`: The S3 bucket used for mapping to and from the FSx filesystem
- `export_path`: Available with `Scratch` and `Persistent_1` deployment types. Specifies the path in the Amazon S3 bucket where the root of your Amazon FSx file system is exported. The path will use the same Amazon S3 bucket as specified in `data_bucket_name`. You can provide an optional prefix to which new and changed data is to be exported from your Amazon FSx for Lustre file system. If an ExportPath value is not provided, Amazon FSx sets a default export path, s3://import-bucket/FSxLustre[creation-timestamp] . The timestamp is in UTC format, for example s3://import-bucket/FSxLustre20181105T222312Z . The Amazon S3 export bucket must be the same as the import bucket specified by ImportPath . If you specify only a bucket name, such as s3://import-bucket, you get a 1:1 mapping of file system objects to S3 bucket objects. This mapping means that the input data in S3 is overwritten on export. If you provide a custom prefix in the export path, such as s3://import-bucket/[custom-optional-prefix] , Amazon FSx exports the contents of your file system to that export prefix in the Amazon S3 bucket.
  - This parameter is not supported for file systems using the `Persistent_2` deployment type.
- `import_path`: The path to the Amazon S3 bucket that you’re using as the data repository for your Amazon FSx for Lustre file system. The root of your FSx for Lustre file system will be mapped to the root of the Amazon S3 bucket you select. If you specify a prefix for the Amazon S3 bucket name, only object keys with that prefix are loaded into the file system.
  - This parameter is not supported for Lustre file systems using the Persistent_2 deployment type.
- `storage_throughput`: Required with `PERSISTENT_1` and `PERSISTENT_2` deployment types, provisions the amount of read and write throughput for each 1 tebibyte (TiB) of file system storage capacity, in MB/s/TiB. File system throughput capacity is calculated by multiplying ﬁle system storage capacity (TiB) by the PerUnitStorageThroughput (MB/s/TiB). For a 2.4-TiB ﬁle system, provisioning 50 MB/s/TiB of PerUnitStorageThroughput yields 120 MB/s of ﬁle system throughput. You pay for the amount of throughput that you provision.
  - For `PERSISTENT_1` SSD storage: 50, 100, 200 MB/s/TiB.
  - For `PERSISTENT_1` HDD storage: 12, 40 MB/s/TiB.
  - For `PERSISTENT_2` SSD storage: 125, 250, 500, 1000 MB/s/TiB.

#### Input Example
module manifest example:

```yaml
name: storage
path: modules/core/fsx-lustre/
parameters:
  - name: private_subnet_ids
    value: [subnet-abc1234]
  - name: vpc_id
    value: vpc-123abc34
  - name: data_bucket_name
    value: data_bucket_name
  - name: fs_deployment_type
    value: PERSISTENT_2
  - name: storage_throughput
    value: 250
```
### Module Metadata Outputs



#### Output Example

```json
{
    "FSxLustreAttrDnsName":"fs-00abc1234efdcg567.fsx.us-east-2.amazonaws.com",
    "FSxLustreFileSystemId":"fs-00a12bc345defg78",
    "FSxLustreSecurityGroup":"sg-0a1b2c3e4d5e6g7j7h",
    "FSxLustreMountName":"123abc45",
    "FSxLustreFileSystemDeploymentType":"PERSISTENT_2"
}
```