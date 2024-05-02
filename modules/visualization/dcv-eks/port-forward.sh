#!/usr/bin/env bash

echo "Ensure session manager installed"
session-manager-plugin

NODE_ROUTE="127.0.0.1"
REGION=${AWS_REGION:-eu-central-1}

if [[ "$?" -eq 0 ]];
then
  echo "aws session manager seems to be already installed"
else
  echo "aws session manager seems to have not been installed. Check installation guide:"
  echo "https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-debian.html"
  exit 1
fi

# Get a list of running instance names and IDs
instance_names=$(aws ec2 describe-instances --region $REGION --filters Name=instance-state-code,Values=16 --query 'Reservations[*].Instances[*].{Name:Tags[?Key==`Name`].Value | [0],ID:InstanceId}' --output text )

# Print the running instance names with numbers
echo "Available running instances:"
echo "$instance_names" | awk '{print NR".",$0}'

# Ask the user to select a running instance
read -p "Enter the number of the running instance you would like to select: " selection

# Get the instance ID for the selected instance
instance_id=$(echo "$instance_names" | awk -v sel="$selection" 'NR==sel {print $1}')

echo "Opening connection to DCV on $instance_id, you can reach it by connecting with NiceDCV Client on port 31980"
# Port forward to Remote host via Instance
aws ssm start-session --target $instance_id \
                       --document-name AWS-StartPortForwardingSession \
                       --parameters '{"portNumber":["31980"],"localPortNumber":["31980"]}' \
                       --region $REGION
