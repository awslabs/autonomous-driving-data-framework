import aws_cdk as cdk
import cdk_nag
import pytest
from aws_cdk.assertions import Annotations, Match, Template


@pytest.fixture(scope="function")
def app() -> cdk.App:
    return cdk.App()


@pytest.fixture(scope="function")
def rbac_stack(app: cdk.App) -> cdk.Stack:
    from rbac_stack import EmrEksRbacStack

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}-rbac"

    return EmrEksRbacStack(
        scope=app,
        id=app_prefix,
        project=project_name,
        deployment=dep_name,
        module=mod_name,
        env=cdk.Environment(
            account="111111111111",
            region="us-east-1",
        ),
        eks_cluster_name="test-cluster",
        eks_admin_role_arn="arn:aws:iam::111111111111:role/test-role",
        eks_oidc_arn="arn:aws:iam::111111111111:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/XXXXXX",
        eks_openid_issuer="oidc.eks.us-east-1.amazonaws.com/id/XXXXXX",
        emr_namespace="emr-studio",
    )


@pytest.fixture(scope="function")
def studio_stack(app: cdk.App) -> cdk.Stack:
    from studio_stack import StudioLiveStack

    project_name = "test-project"
    dep_name = "test-deployment"
    mod_name = "test-module"
    app_prefix = f"{project_name}-{dep_name}-{mod_name}"

    return StudioLiveStack(
        scope=app,
        id=app_prefix,
        project=project_name,
        deployment=dep_name,
        module=mod_name,
        env=cdk.Environment(
            account="111111111111",
            region="us-east-1",
        ),
        vpc_id="vpc-123",
        private_subnet_ids=["subnet12", "subnet34"],
        artifact_bucket_name="test-bucket",
        eks_cluster_name="test-cluster",
        execution_role_arn="arn:aws:iam::111111111111:role/test-role",
        emr_namespace="test-namespace",
        sso_username="test-user",
    )


def test_synthesize_stack(rbac_stack: cdk.Stack, studio_stack: cdk.Stack) -> None:
    Template.from_stack(rbac_stack)
    Template.from_stack(studio_stack)


def test_no_cdk_nag_errors(rbac_stack: cdk.Stack, studio_stack: cdk.Stack) -> None:
    cdk.Aspects.of(rbac_stack).add(cdk_nag.AwsSolutionsChecks())
    cdk.Aspects.of(studio_stack).add(cdk_nag.AwsSolutionsChecks())

    nag_errors = Annotations.from_stack(rbac_stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    ) + Annotations.from_stack(studio_stack).find_error(
        "*",
        Match.string_like_regexp(r"AwsSolutions-.*"),
    )
    assert not nag_errors, f"Found {len(nag_errors)} CDK nag errors"
