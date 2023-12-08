# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest

import boto3
from moto import mock_ec2

import helpers


class TestHelperMethods(unittest.TestCase):
    def test__get_ami_version_from_file(self):
        eks_version = "1.25"

        result = helpers._get_ami_version_from_file(eks_version)
        self.assertEqual(result, "1.25.7-20230406")

    def test__get_chart_release_from_file(self):
        eks_version = "1.25"
        workload = "alb_controller"

        result = helpers._get_chart_release_from_file(eks_version, workload)
        self.assertEqual(result, "aws-load-balancer-controller")

    def test__get_chart_release_from_file_non_default(self):
        eks_version = "1.25"
        workload = "test_workload"

        result = helpers._get_chart_release_from_file(eks_version, workload)
        self.assertEqual(result, "test-workload")

    def test__get_chart_repo_from_file(self):
        eks_version = "1.25"
        workload = "alb_controller"

        result = helpers._get_chart_repo_from_file(eks_version, workload)
        self.assertEqual(result, "https://aws.github.io/eks-charts")

    def test__get_chart_repo_from_file_non_default(self):
        eks_version = "1.25"
        workload = "test_workload"

        result = helpers._get_chart_repo_from_file(eks_version, workload)
        self.assertEqual(result, "https://kubernetes-sigs.github.io/test-workload/charts")

    def test__get_chart_version_from_file(self):
        eks_version = "1.25"
        workload = "alb_controller"

        result = helpers._get_chart_version_from_file(eks_version, workload)
        self.assertEqual(result, "1.4.8")

    def test__get_chart_version_from_file_non_default(self):
        eks_version = "1.25"
        workload = "test_workload"

        result = helpers._get_chart_version_from_file(eks_version, workload)
        self.assertEqual(result, "1.0.1")

    def test__parse_versions_file(self):
        eks_version = "1.25"

        self.assertEqual(helpers._parse_versions_file(eks_version), None)

    def test_deep_merge(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        d3 = {"c": 5, "d": 6}

        result = helpers.deep_merge(d1, d2, d3)
        self.assertEqual(result, {"a": 1, "b": 3, "c": 5, "d": 6})

    def test_get_ami_version(self):
        eks_version = "1.25"

        result = helpers.get_ami_version(eks_version)
        self.assertEqual(result, "1.25.7-20230406")

    @mock_ec2
    def test_get_az_from_subnet(self):
        boto3.setup_default_session()
        ec2 = boto3.resource("ec2", region_name="us-east-1")
        client = boto3.client("ec2", region_name="us-east-1")
        vpc = ec2.create_vpc(CidrBlock="172.31.0.0/16")
        subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="172.31.48.0/20", AvailabilityZone="us-east-1a")
        subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="172.31.64.0/20", AvailabilityZone="us-east-1b")
        subnet1_result = client.describe_subnets(SubnetIds=[subnet1.id])["Subnets"]
        subnet2_result = client.describe_subnets(SubnetIds=[subnet2.id])["Subnets"]

        az_subnet_map = helpers.get_az_from_subnet([subnet1.id, subnet2.id])
        self.assertEqual(
            az_subnet_map,
            {
                subnet1.id: subnet1_result[0]["AvailabilityZone"],
                subnet2.id: subnet2_result[0]["AvailabilityZone"],
            },
        )

    def test_get_chart_release(self):
        eks_version = "1.25"
        workload = "alb_controller"

        result = helpers.get_chart_release(eks_version, workload)
        self.assertEqual(result, "aws-load-balancer-controller")

    def test_get_chart_repo(self):
        eks_version = "1.25"
        workload = "alb_controller"

        result = helpers.get_chart_repo(eks_version, workload)
        self.assertEqual(result, "https://aws.github.io/eks-charts")

    def test_get_chart_values(self):
        workload = "alb_controller"
        data = {"charts": {"alb_controller": {"values": {"image": {"repository": "test"}}}}}

        result = helpers.get_chart_values(data, workload)
        self.assertEqual(result, {"image": {"repository": "test"}})

    def test_get_chart_version(self):
        eks_version = "1.25"
        workload = "alb_controller"

        result = helpers.get_chart_version(eks_version, workload)
        self.assertEqual(result, "1.4.8")
