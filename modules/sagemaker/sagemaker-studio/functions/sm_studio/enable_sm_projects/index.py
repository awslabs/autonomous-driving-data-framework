import boto3
import cfnresponse
from botocore.exceptions import ClientError

sm_client = boto3.client("sagemaker")
sc_client = boto3.client("servicecatalog")


def handler(event, context):
    try:
        if "RequestType" in event and event["RequestType"] in {"Create", "Update"}:
            properties = event["ResourceProperties"]
            roles = properties.get("ExecutionRoles", [])

            for role in roles:
                enable_sm_projects(role)

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, "")
    except ClientError as exception:
        print(exception)
        cfnresponse.send(
            event,
            context,
            cfnresponse.FAILED,
            {},
            physicalResourceId=event.get("PhysicalResourceId"),
        )


def enable_sm_projects(studio_role_arn):
    # enable Project on account level (accepts portfolio share)
    response = sm_client.enable_sagemaker_servicecatalog_portfolio()

    print(response)

    # associate studio role with portfolio
    response = sc_client.list_accepted_portfolio_shares()

    print(response)

    portfolio_id = ""

    for portfolio in response["PortfolioDetails"]:
        if portfolio["ProviderName"] == "Amazon SageMaker":
            portfolio_id = portfolio["Id"]
            break

    response = sc_client.associate_principal_with_portfolio(
        PortfolioId=portfolio_id, PrincipalARN=studio_role_arn, PrincipalType="IAM"
    )

    print(response)
