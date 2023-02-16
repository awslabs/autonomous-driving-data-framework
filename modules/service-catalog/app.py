import os

from aws_cdk import App, CfnOutput, Environment

from stack import ServiceCatalogStack

deployment_name = os.getenv("ADDF_DEPLOYMENT_NAME", "")
module_name = os.getenv("ADDF_MODULE_NAME", "")

app = App()


def _param(name: str) -> str:
    return f"ADDF_PARAMETER_{name}"


DEFAULT_PORTFOLIO_ACCESS_ROLE_ARN = None

portfolio_access_role_arn = os.getenv(
    _param("PORTFOLIO_ACCESS_ROLE_ARN"), DEFAULT_PORTFOLIO_ACCESS_ROLE_ARN
)


stack = ServiceCatalogStack(
    scope=app,
    id=f"addf-{deployment_name}-{module_name}",
    deployment_name=deployment_name,
    module_name=module_name,
    portfolio_access_role_arn=portfolio_access_role_arn,
    env=Environment(
        account=os.environ["CDK_DEFAULT_ACCOUNT"],
        region=os.environ["CDK_DEFAULT_REGION"],
    ),
)


CfnOutput(
    stack,
    "PortfolioARN",
    value=stack.portfolio.portfolio_arn,
)
if portfolio_access_role_arn is not None:
    CfnOutput(
        stack,
        "PortfolioAccessRoleName",
        value=stack.portfolio_access_role.role_name,
    )
    CfnOutput(
        stack,
        "PortfolioAccessRoleARN",
        value=stack.portfolio_access_role.role_arn,
    )

app.synth(force=True)
