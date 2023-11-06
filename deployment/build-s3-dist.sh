#!/bin/bash

# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#sudo yum-config-manager --enable epel
#sudo yum update -y
#sudo pip install --upgrade pip
#alias sudo='sudo env PATH=$PATH'
#sudo  pip install --upgrade setuptools
#sudo pip install --upgrade virtualenv

# This script should be run from the repo's deployment directory
# cd deployment
# ./build-s3-dist.sh source-bucket-base-name
# source-bucket-base-name should be the base name for the S3 bucket location where the template will source the Lambda code from.
# The template will append '-[region_name]' to this bucket name.
# For example: ./build-s3-dist.sh solutions
# The template will then expect the source code to be located in the solutions-[region_name] bucket

# Check to see if input has been provided:
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]|| [ -z "$4" ] ; then
    echo "Please provide the base source bucket name and version (subfolder) where the lambda code will eventually reside.\nFor example: ./build-s3-dist.sh solutions solutions-github trademarked-solution-name v1.0"
    exit 1
fi

# Build source
echo "Staring to build distribution"
# export deployment_dir=`pwd`
# export dist_dir="$deployment_dir"
export dist_dir="deployment"
export create_template="deployment/scene-intelligence-with-rosbag-on-aws-create.template"
export delete_template="deployment/scene-intelligence-with-rosbag-on-aws-delete.template"
template_dist_dir="$dist_dir/global-s3-assets"
opensrc_dist_dir="$dist_dir/open-source"
build_dist_dir="$dist_dir/regional-s3-assets"

echo "------------------------------------------------------------------------------"
	 echo "[Init] Clean old dist folders"
echo "------------------------------------------------------------------------------"

echo "Creating distribution directory"
mkdir -p dist
echo "rm -rf $template_dist_dir"
rm -rf $template_dist_dir
echo "mkdir -p $template_dist_dir"
mkdir -p $template_dist_dir
echo "rm -rf $build_dist_dir"
rm -rf $build_dist_dir
echo "mkdir -p $build_dist_dir"
mkdir -p $build_dist_dir
echo "rm -rf $opensrc_dist_dir"
rm -rf $opensrc_dist_dir
echo "mkdir -p $opensrc_dist_dir"
mkdir -p $opensrc_dist_dir


echo "In deployment folder"
pwd

echo "Replacing solution bucket in the template"
cp -f $create_template $template_dist_dir
cp -f $delete_template $template_dist_dir

echo "Placeholder: Pushing single click CFN stack into build_dist_dir to make it non-empty. Empty dirs are being ignored in Codepipeline and failing to execute the deployAssets stage"
cp -f $create_template $build_dist_dir 
cp -f $delete_template $build_dist_dir 

echo "Placeholder: Pushing single click CFN stack into opensrc_dist_dir to make it non-empty. Empty dirs are being ignored in Codepipeline and failing to execute the deployAssets stage"
cp -f $create_template $opensrc_dist_dir 
cp -f $delete_template $opensrc_dist_dir 
