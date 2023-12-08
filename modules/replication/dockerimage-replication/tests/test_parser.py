# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest

from helmparser.parser import parser


class TestParser(unittest.TestCase):
    def test__get_branch(self):
        data = {"location": "values", "path": "image.repository"}
        result = parser._get_branch(data)
        self.assertEqual(result, ["image", "repository"])

        data = {
            "location": "values",
            "path": "image.repository",
            "subchart": "ui",
        }
        result = parser._get_branch(data)
        self.assertEqual(result, ["ui", "image", "repository"])

    def test__add_branch(self):
        test_dict = {"image": {"repository": "test"}}
        branch = ["image", "tag"]
        value = "1.0.0"
        result = parser._add_branch(test_dict, branch, value)
        self.assertEqual(result, {"image": {"repository": "test", "tag": "1.0.0"}})

    def test__get_dictionary_value_by_dot_separated_key(self):
        test_dict = {"image": {"repository": "test", "tag": "1.0.0"}}
        key = "image.tag"
        result = parser._get_dictionary_value_by_dot_separated_key(test_dict, key)
        self.assertEqual(result, "1.0.0")

    def test__parse_versions_file(self):
        versions_dir = "tests/test_versions"
        eks_version = "1.21"

        result = parser._parse_versions_file(versions_dir, eks_version)
        self.assertEqual(
            result,
            {
                "ami": {"version": "1.21.14-20230217"},
                "charts": {
                    "alb_controller": {"version": "1.3.3"},
                    "cluster_autoscaler": {"replication": {"cluster_autoscaler": {"tag": "v1.26.2"}}},
                    "kyverno": {"skip": True},
                },
                "additional_images": {
                    "cloudwatch_agent": "public.ecr.aws/cloudwatch-agent/cloudwatch-agent:1.247358.0b252413",
                    "secrets_store_csi_driver_provider_aws": "public.ecr.aws/aws-secrets-manager/secrets-store-csi-driver-provider-aws:1.0.r2-2021.08.13.20.34-linux-amd64",
                },
            },
        )

    def test__needs_custom_replication(self):
        # Test true
        data = {"replication": {"cluster_autoscaler": "image.repository"}}
        image_name = "cluster_autoscaler"
        type_of_value = "repository"

        result = parser._needs_custom_replication(data, image_name, type_of_value)
        self.assertTrue(result)

        # Test missing replication key
        data = {"noreplication": {"cluster_autoscaler": "image.repository"}}
        image_name = "cluster_autoscaler"
        type_of_value = "repository"

        # Test different image name
        result = parser._needs_custom_replication(data, image_name, type_of_value)
        self.assertFalse(result)
        data = {"replication": {"cluster_autoscaler": "image.repository"}}
        image_name = "other_image"
        type_of_value = "repository"

        result = parser._needs_custom_replication(data, image_name, type_of_value)
        self.assertFalse(result)

        # Test different type of value
        data = {"replication": {"cluster_autoscaler": "image.repository"}}
        image_name = "cluster_autoscaler"
        type_of_value = "tag"

        result = parser._needs_custom_replication(data, image_name, type_of_value)
        self.assertFalse(result)

    def test_add_branch_to_dict(self):
        test_dict = {"image": {"repository": "test"}}
        test_data = {"path": "image.tag"}
        value = "1.0.0"
        result = parser.add_branch_to_dict(test_dict, test_data, value)
        self.assertEqual(result, {"image": {"repository": "test", "tag": "1.0.0"}})

    def test_get_ami_version(self):
        versions_dir = "tests/test_versions"
        eks_version = "1.21"

        result = parser.get_ami_version(versions_dir, eks_version)
        self.assertEqual(result, "1.21.14-20230217")

        eks_version = "default"

        result = parser.get_ami_version(versions_dir, eks_version)
        self.assertEqual(result, "")

    def test_get_additional_images(self):
        versions_dir = "tests/test_versions"
        eks_version = "1.21"

        result = parser.get_additional_images(versions_dir, eks_version)
        self.assertEqual(
            result,
            {
                "cloudwatch_agent": "public.ecr.aws/cloudwatch-agent/cloudwatch-agent:1.247358.0b252413",
                "secrets_store_csi_driver_provider_aws": "public.ecr.aws/aws-secrets-manager/secrets-store-csi-driver-provider-aws:1.0.r2-2021.08.13.20.34-linux-amd64",
            },
        )

        eks_version = "default"

        result = parser.get_additional_images(versions_dir, eks_version)
        self.assertEqual(result, {})

    def test_get_workloads(self):
        versions_dir = "tests/test_versions"
        eks_version = "1.21"

        result = parser.get_workloads(versions_dir, eks_version)

        self.assertEqual(
            result,
            {
                "alb_controller": {
                    "name": "aws-load-balancer-controller",
                    "repository": "https://aws.github.io/eks-charts",
                    "version": "1.3.3",
                    "images": {
                        "alb_controller": {
                            "repository": {
                                "location": "values",
                                "path": "image.repository",
                            },
                            "tag": {"location": "values", "path": "image.tag"},
                        }
                    },
                },
                "cluster_autoscaler": {
                    "name": "cluster-autoscaler",
                    "repository": "https://kubernetes.github.io/autoscaler",
                    "version": "9.11.0",
                    "images": {
                        "cluster_autoscaler": {
                            "repository": {
                                "location": "values",
                                "path": "image.repository",
                            },
                            "tag": {"location": "values", "path": "image.tag"},
                        }
                    },
                    "replication": {"cluster_autoscaler": {"tag": "v1.26.2"}},
                },
            },
        )

    def test_parse_value(self):
        workload = {
            "values": {
                "image": {
                    "repository": "public.ecr.aws/eks/aws-load-balancer-controller",
                    "tag": "v2.4.7",
                    "pullPolicy": "IfNotPresent",
                },
            },
        }
        values = {
            "name": "aws-load-balancer-controller",
            "repository": "https://aws.github.io/eks-charts",
            "version": "1.4.8",
            "images": {
                "alb_controller": {
                    "repository": {"location": "values", "path": "image.repository"},
                    "tag": {"location": "values", "path": "image.tag"},
                }
            },
        }
        image_name = "alb_controller"
        image_data = {"location": "values", "path": "image.tag"}
        value_name = "tag"

        result = parser.parse_value(workload, values, image_name, image_data, value_name)

        self.assertEqual(result, "v2.4.7")

        values = {
            "name": "aws-load-balancer-controller",
            "repository": "https://aws.github.io/eks-charts",
            "version": "1.4.8",
            "replication": {"alb_controller": {"tag": "v2.4.8"}},
            "images": {
                "alb_controller": {
                    "repository": {"location": "values", "path": "image.repository"},
                    "tag": {"location": "values", "path": "image.tag"},
                },
            },
        }

        result = parser.parse_value(workload, values, image_name, image_data, value_name)

        self.assertEqual(result, "v2.4.8")

        workload = {
            "subcharts": {
                "some": {
                    "values": {
                        "image": {
                            "repository": "public.ecr.aws/eks/aws-load-balancer-controller",
                            "tag": "v2.4.9",
                            "pullPolicy": "IfNotPresent",
                        },
                    },
                }
            }
        }

        values = {
            "name": "aws-load-balancer-controller",
            "repository": "https://aws.github.io/eks-charts",
            "version": "1.4.8",
            "images": {
                "alb_controller": {
                    "repository": {"location": "values", "path": "image.repository"},
                    "tag": {"location": "values", "path": "image.tag"},
                },
            },
        }

        image_data = {
            "subchart": "some",
            "location": "values",
            "path": "image.tag",
        }

        result = parser.parse_value(workload, values, image_name, image_data, value_name)

        self.assertEqual(result, "v2.4.9")

        workload = {
            "values": {
                "image": {
                    "repository": "public.ecr.aws/eks/aws-load-balancer-controller",
                    "tag": "2.5.0",
                    "pullPolicy": "IfNotPresent",
                },
            },
        }
        values = {
            "name": "aws-load-balancer-controller",
            "repository": "https://aws.github.io/eks-charts",
            "version": "1.4.8",
            "images": {
                "alb_controller": {
                    "repository": {"location": "values", "path": "image.repository"},
                    "tag": {"location": "values", "path": "image.tag"},
                }
            },
        }
        image_data = {"location": "values", "path": "image.tag", "prefix": "v"}

        result = parser.parse_value(workload, values, image_name, image_data, value_name)

        self.assertEqual(result, "v2.5.0")


if __name__ == "__main__":
    unittest.main()

    print("Everything passed")
