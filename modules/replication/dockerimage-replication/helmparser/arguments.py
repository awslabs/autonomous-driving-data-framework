"""Argument parsing module"""
import argparse

parser = argparse.ArgumentParser(
    description="Generates list of images to sync",
)

parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    dest="verbosity",
    help="increase verbosity",
)

parser.add_argument(
    "-u",
    "--update-helm-repos",
    action="store_true",
    dest="update_helm",
    help="update helm repositories",
)

parser.add_argument(
    "-e",
    "--eks-version",
    action="store",
    default="1.25",
    dest="eks_version",
    help="specify eks version",
    type=str,
)

parser.add_argument(
    "-d",
    "--versions-directory",
    action="store",
    dest="versions_dir",
    help="provide path to the versions directory",
    type=str,
    required=True,
)

parser.add_argument(
    "-p",
    "--registry-prefix",
    action="store",
    dest="registry_prefix",
    help="provide registry prefix",
    type=str,
    required=True,
)

args = parser.parse_args()
