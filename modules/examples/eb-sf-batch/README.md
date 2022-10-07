## Description

This module shows a pattern of using AWS Event bridge "Cron Based" invocation triggering AWS Step Functions further triggering AWS Batch jobs.

## Inputs/Outputs


### Input Parameters

- `ecr-repo-name` Provide your ECR Repo name, which will be further stitched with `project-name`, `dep_name` and `module_name`
- `fargate-job-queue-arn` Provide your Batch queue ARN (EC2 or Fargate). For the demo, the pattern uses fargate batch queue arn
- `vcpus` Provide VCPUS count for your Batch definition
- `memory_limit_mib` Provide Memory limits for your Batch definition by referring to the [link](https://docs.aws.amazon.com/batch/latest/userguide/job_definition_parameters.html)


#### Input Example

```yaml
name: eb-sf-batch
path: modules/examples/eb-sf-batch/
parameters:
  - name: ecr-repo-name
    value: mlops-test
  - name: fargate-job-queue-arn
    valueFrom:
      moduleMetadata:
        group: core
        name: batch-compute
        key: FargateJobQueueArn
  - name: vcpus
    value: 2
  - name: memory_limit_mib
    value: 4096
```