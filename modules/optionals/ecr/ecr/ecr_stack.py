from aws_cdk import CfnOutput, Duration, Stack, aws_ecr as ecr
from constructs import Construct

IMAGE_MUTABILITY = {
    "IMMUTABLE": ecr.TagMutability.IMMUTABLE,
    "MUTABLE": ecr.TagMutability.MUTABLE,
}


class EcrStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        repository_name,
        image_tag_mutability,
        lifecycle_max_image_count,
        lifecycle_max_days,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.repository = ecr.Repository(
            self,
            f"addf-{repository_name}",
            repository_name=repository_name,
            image_tag_mutability=IMAGE_MUTABILITY[image_tag_mutability],
        )

        if lifecycle_max_days is not None:
            self.repository.add_lifecycle_rule(max_image_age=Duration.days(lifecycle_max_days))
            CfnOutput(
                self,
                "LifecycleMaxDays",
                value=lifecycle_max_days,
            )

        if lifecycle_max_image_count is not None:
            self.repository.add_lifecycle_rule(max_image_count=lifecycle_max_image_count)
            CfnOutput(
                self,
                "LifecycleMaxImages",
                value=lifecycle_max_image_count,
            )

        CfnOutput(
            self,
            "RepositoryName",
            value=self.repository.repository_name,
        )

        CfnOutput(
            self,
            "RepositoryARN",
            value=self.repository.repository_arn,
        )
