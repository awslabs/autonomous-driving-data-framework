# Metadata Storage


## Description

This module creates reusable storage components.

The following functions occur:

- creates a Glue Database table for vsi data
- create a DDB table for Rosbag-BagFile-Metadata
- creates a DDB table for Rosbag-Scene-Metadata
- creates an Event Bridge Bus

## Inputs/Outputs

### Input Paramenters

#### Required

- `glue-db-suffix`: The suffix to post-pend to the name of the glue database
- `rosbag-bagfile-table-suffix`: The suffix to post-pend to the DDB table name for Rosbag Bagfile Data
- `rosbag-scene-table-suffix`: The suffix to post-pend to the DDB table name for Rosbag Scene Data

#### Optional


### Module Metadata Outputs

- `GlueDBName`: name of the Glue DB created
- `RosbagBagFileTable`: name of the DDB table created for Rosbag Bagfile Data
- `RosbagSceneMetadataTable`: name of the DDB table created for Rosbag Scene Data
- `RosbagSceneMetadataStreamArn`: arn of the stream for the Rosbag Scene Metadata Table
- `EventBusName`: name of the event bus in Event Bridge
- `EventBusArn`: arn of the event bus in Event Bridge
#### Output Example

```json
{
  "GlueDBName": "some-db-name",
  "RosbagBagFileTable": "some-table-name",
  "RosbagSceneMetadataTable": "some-table-name",
  "RosbagSceneMetadataStreamArn": "arn:aws:dynamodb:<region>:table/addf-local-core-metadata-storage-<name>",
  "EventBusName":"addf-example-dev-core-metadata-storage",
  "EventBusArn":"arn:aws:events:<region>:<account-id>:event-bus/addf-example-dev-core-metadata-storage"
}
```
