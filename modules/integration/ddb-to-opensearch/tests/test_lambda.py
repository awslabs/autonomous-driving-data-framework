#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License").
#    You may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import importlib
import os
import sys

import pytest
import requests.exceptions

sys.path.append("./lambda")
lambda_module = importlib.import_module("lambda.index")


test_json = {
    "Records": [
        {
            "eventID": "7846dd21c5e01f654581450431afb8a2",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244975E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824497.5"},
                    "end_time": {"N": "1605824497.6"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244975E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.09999990463256836"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "1"},
                },
                "SequenceNumber": "5026100000000049631196383",
                "SizeBytes": 508,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-stream/2022-03-22T17:49:16.334",
        },
        {
            "eventID": "be9bb1f9afef0d505a652fce4ce62201",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244963E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824496.3"},
                    "end_time": {"N": "1605824496.5"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244963E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.20000004768371582"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "3"},
                },
                "SequenceNumber": "5026200000000049631196463",
                "SizeBytes": 508,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-/stream/2022-03-22T17:49:16.334",
        },
        {
            "eventID": "861ef9134bf08e34f54d427a483a1242",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244969E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824496.9"},
                    "end_time": {"N": "1605824497.1"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244969E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.19999980926513672"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "6"},
                },
                "SequenceNumber": "5026300000000049631196464",
                "SizeBytes": 508,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-/stream/2022-03-22T17:49:16.334",
        },
        {
            "eventID": "5faeff53880e6ab6e26e590daebed219",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244995E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824499.5"},
                    "end_time": {"N": "1605824499.6"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244995E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.09999990463256836"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "3"},
                },
                "SequenceNumber": "5026400000000049631196465",
                "SizeBytes": 508,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-/stream/2022-03-22T17:49:16.334",
        },
        {
            "eventID": "b78fb2f2b3bdaf92085bf49857310102",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.605824499E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824499"},
                    "end_time": {"N": "1605824499.1"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.605824499E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.09999990463256836"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "1"},
                },
                "SequenceNumber": "5026500000000049631196467",
                "SizeBytes": 505,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-/stream/2022-03-22T17:49:16.334",
        },
    ]
}


test_bad_json = {
    "Records": [
        {
            "eventID": "7846dd21c5e01f654581450431afb8a2",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id_adfasdfas": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244975E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824497.5"},
                    "end_time": {"N": "1605824497.6"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244975E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.09999990463256836"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "1"},
                },
                "SequenceNumber": "5026100000000049631196383",
                "SizeBytes": 508,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-/stream/2022-03-22T17:49:16.334",
        },
        {
            "eventID": "be9bb1f9afef0d505a652fce4ce62201",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244963E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824496.3"},
                    "end_time": {"N": "1605824496.5"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244963E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.20000004768371582"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "3"},
                },
                "SequenceNumber": "5026200000000049631196463",
                "SizeBytes": 508,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-/stream/2022-03-22T17:49:16.334",
        },
        {
            "eventID": "861ef9134bf08e34f54d427a483a1242",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244969E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824496.9"},
                    "end_time": {"N": "1605824497.1"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244969E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.19999980926513672"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "6"},
                },
                "SequenceNumber": "5026300000000049631196464",
                "SizeBytes": 508,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-/stream/2022-03-22T17:49:16.334",
        },
        {
            "eventID": "5faeff53880e6ab6e26e590daebed219",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244995E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824499.5"},
                    "end_time": {"N": "1605824499.6"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.6058244995E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.09999990463256836"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "3"},
                },
                "SequenceNumber": "5026400000000049631196465",
                "SizeBytes": 508,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-/stream/2022-03-22T17:49:16.334",
        },
        {
            "eventID": "b78fb2f2b3bdaf92085bf49857310102",
            "eventName": "INSERT",
            "eventVersion": "1.1",
            "eventSource": "aws:dynamodb",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "ApproximateCreationDateTime": 1647975184.0,
                "Keys": {
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.605824499E9"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                },
                "NewImage": {
                    "start_time": {"N": "1605824499"},
                    "end_time": {"N": "1605824499.1"},
                    "scene_id": {"S": "small1__2020-11-19-16-21-22_4_PersonInLane_1.605824499E9"},
                    "topics_analyzed": {
                        "S": "rgb_right_detections_only_clean,post_process_lane_points_rgb_front_right_clean"
                    },
                    "bag_file_prefix": {"S": "rosbag-scene-detection/small1__2020-11-19-16-21-22_4.bag"},
                    "bag_file_bucket": {"S": "addf-local-raw-bucket-us-east-1-123456789012"},
                    "scene_length": {"N": "0.09999990463256836"},
                    "bag_file": {"S": "small1__2020-11-19-16-21-22_4"},
                    "num_people_in_scene_start": {"N": "1"},
                },
                "SequenceNumber": "5026500000000049631196467",
                "SizeBytes": 505,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            },
            "eventSourceARN": "arn:aws:dynamodb:us-east-1:123456789012:table/addf-/stream/2022-03-22T17:49:16.334",
        },
    ]
}


@pytest.fixture(scope="function")
def stack_defaults():

    os.environ[
        "DOMAIN_ENDPOINT"
    ] = "pc-addf-aws-solutions--367e660c-k57drotm5ampt5nt7ftfnse4pi.us-west-2.es.amazonaws.com"
    os.environ["REGION"] = "us-east-1"


def test_lambda(stack_defaults, requests_mock):
    try:
        lambda_module.handler(test_json, None)
    except requests.exceptions.InvalidURL:
        pass


def test_missing_domain(stack_defaults):
    del os.environ["DOMAIN_ENDPOINT"]
    with pytest.raises(requests.exceptions.InvalidURL):
        lambda_module.handler(test_json, None)


def test_bad_payload(stack_defaults):
    try:
        lambda_module.handler(test_bad_json, None)
    except KeyError:
        pass
