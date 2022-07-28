"""
UTIL FOR TESTING ONLY - DELETES ALL ENTRIES IN THE DYNAMODB TRACKING TABLE
python empty_dynamo.py

"""
import boto3

from dag_config import DYNAMODB_TABLE

dynamo = boto3.resource("dynamodb")


def truncateTable(tableName):
    table = dynamo.Table(tableName)

    # get the table keys
    tableKeyNames = [key.get("AttributeName") for key in table.key_schema]

    # Only retrieve the keys for each item in the table (minimize data transfer)
    ProjectionExpression = ", ".join(tableKeyNames)

    response = table.scan(ProjectionExpression=ProjectionExpression)
    data = response.get("Items")

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ProjectionExpression=ProjectionExpression,
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        data.extend(response["Items"])

    with table.batch_writer() as batch:
        for each in data:
            batch.delete_item(Key={key: each[key] for key in tableKeyNames})


if __name__ == "__main__":
    truncateTable(DYNAMODB_TABLE)
