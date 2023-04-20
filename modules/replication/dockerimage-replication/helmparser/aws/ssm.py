"""AWS functions"""
import boto3
import botocore

from helmparser.logging import boto3_logger as logger

ssm = boto3.client("ssm")


def put_parameter(name: str, value: str) -> None:
    """Creates or updates SSM parameter

    Args:
        name (str): SSM parameter name
        value (str): SSM parameter value

    Raises:
        error: AWS API error
    """
    try:
        ssm.put_parameter(
            Name=name,
            Value=value,
            Type="String",
            Overwrite=True,
        )
    except botocore.exceptions.ClientError as error:
        if error.response["Error"]["Code"] == "InternalServerError":
            logger.error("Internal server error")
        elif error.response["Error"]["Code"] == "InvalidKeyId":
            logger.error("Invalid Key Id")
        elif error.response["Error"]["Code"] == "ParameterLimitExceeded":
            logger.error("Parameter limit exceed")
        elif error.response["Error"]["Code"] == "TooManyUpdates":
            logger.error("Too many updates")
        raise error
