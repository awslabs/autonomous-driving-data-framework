import cdk_nag
from aws_cdk import Aspects, Duration, Stack
from aws_cdk import aws_ecr as ecr
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
            f"{repository_name}",
            repository_name=repository_name,
            image_tag_mutability=IMAGE_MUTABILITY[image_tag_mutability],
        )

        if lifecycle_max_days is not None:
            self.repository.add_lifecycle_rule(
                max_image_age=Duration.days(lifecycle_max_days)
            )

        if lifecycle_max_image_count is not None:
            self.repository.add_lifecycle_rule(
                max_image_count=lifecycle_max_image_count
            )

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())
