---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior.

**Expected behavior**
A clear and concise description of what you expected to happen.

**Please complete the following information about the solution:**
- [ ] Version: [e.g. v1.0.0]

To get the version of the solution, you can look at the description of the created CloudFormation stack. For example, "_(SO0021) - Video On Demand workflow with AWS Step Functions, MediaConvert, MediaPackage, S3, CloudFront and DynamoDB. Version **v5.0.0**_". If you have not yet installed the stack, or are unable to install due to a problem, you can find the version and solution ID in the template with a text editor. Open the .template file and search for `SOLUTION_VERSION` in the content. You will find several matches and they will all be the same value:

```json
    "Environment": {
      "Variables": {
        "SOLUTION_ID": "SO0221",
        "SOLUTION_VERSION": "v1.0.0"
      }
    },
```

This information is also provided in `source/infrastructure/cdk.json`:

```json
    "SOLUTION_ID": "SO0221",
    "SOLUTION_VERSION": "v1.0.0",
```



- [ ] Region: [e.g. us-east-1]
- [ ] Was the solution modified from the version published on this repository?
- [ ] If the answer to the previous question was yes, are the changes available on GitHub?
- [ ] Have you checked your [service quotas](https://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html) for the sevices this solution uses?
- [ ] Were there any errors in the CloudWatch Logs?

**Screenshots**
If applicable, add screenshots to help explain your problem (please **DO NOT include sensitive information**).

**Additional context**
Add any other context about the problem here.
