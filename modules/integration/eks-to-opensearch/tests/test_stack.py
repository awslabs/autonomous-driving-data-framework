import aws_cdk as cdk
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match, Template


@pytest.fixture(scope="function")
def app() -> cdk.App:
    return cdk.App()


@pytest.fixture(scope="function")
def stack(app: cdk.App) -> cdk.Stack:
    from stack import EksOpenSearchIntegrationStack

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    return EksOpenSearchIntegrationStack(
        scope=app,
        id=app_prefix,
        project=project_name,
        deployment=dep_name,
        module=mod_name,
        env=cdk.Environment(
            account="111111111111",
            region="us-east-1",
        ),
        opensearch_sg_id="sg-xxx",
        opensearch_domain_endpoint="xxxxxxx.us-east-1.es.amazonaws.com",
        eks_cluster_name="test-cluster",
        eks_admin_role_arn="arn:aws:iam::111111111111:role/test-role",
        eks_cluster_sg_id="sg-yyy",
        eks_oidc_arn="arn:aws:iam::111111111111:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/XXXXXX",
    )


def test_synthesize_stack(stack: cdk.Stack) -> None:
    Template.from_stack(stack)


def test_no_cdk_nag_errors(stack: cdk.Stack) -> None:
    cdk.Aspects.of(stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
