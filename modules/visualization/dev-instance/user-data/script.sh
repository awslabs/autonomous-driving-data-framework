Content-Type: multipart/mixed; boundary="//"
MIME-Version: 1.0

--//
Content-Type: text/cloud-config; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="cloud-config.txt"

#cloud-config
cloud_final_modules:
- [scripts-user, always]

--//
Content-Type: text/x-shellscript; charset="us-ascii"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Content-Disposition: attachment; filename="userdata.txt"

#!/bin/bash -xe

echo "Cloud init in progress. Machine will REBOOT after cloud init is complete!!" >/etc/motd


DATA_SERVICE_USER_SECRET_NAME="$DATA_SERVICE_USER_SECRET_NAME_REF"

# Find Ubuntu Version
VERSION=$(lsb_release -a | grep Release | awk -F ":" '{print $2}' | sed -E -e 's/[[:blank:]]+//g')

echo "Detected Ubuntu $VERSION"

# setup graphics desktop
export DEBIAN_FRONTEND=noninteractive
export DEBCONF_NONINTERACTIVE_SEEN=true

# check if we have a GPU and if Nvidia drivers and CUDA need to be installed
[[ ! -x "$(command -v nvidia-smi)" ]] &&
    apt-get update && apt-get -y upgrade &&
    apt-get -y install ubuntu-drivers-common &&
    [[ -n "$(ubuntu-drivers devices | grep nvidia-driver | grep recommended | awk -F " " '{print $3}')" ]] &&
    apt-get -y install "linux-headers-$UNAME_REF" &&
    ( ([[ $VERSION == "18.04" ]] &&
        wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/cuda-ubuntu1804.pin &&
        mv cuda-ubuntu1804.pin /etc/apt/preferences.d/cuda-repository-pin-600 &&
        apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/3bf863cc.pub &&
        add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/ /") ||
        ([[ $VERSION == "20.04" ]] &&
            wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin &&
            mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600 &&
            apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub &&
            add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /")) &&
    apt-get update && apt-get -y purge cuda && apt-get -y purge nvidia-* && apt-get -y autoremove &&
    ubuntu-drivers autoinstall &&
    apt-get -y install cuda &&
    apt-get -y install nvidia-cuda-toolkit &&
    apt-get -y install libcudnn8 &&
    apt-get -y install libcudnn8-dev &&
    reboot

# setup software repo for docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
apt-key fingerprint 0EBFCD88
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# add key for fsx-lustre client
wget -O - https://fsx-lustre-client-repo-public-keys.s3.amazonaws.com/fsx-ubuntu-public-key.asc | apt-key add -

# add key for NICE-DCV
wget https://d1uj6qtbmh3dt5.cloudfront.net/NICE-GPG-KEY
gpg --import NICE-GPG-KEY

# setup software repo for ros
sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

# update and install required packages
apt update
apt install -y git tar apt-transport-https ca-certificates curl jq gnupg-agent software-properties-common

# Store user-data script
curl 169.254.169.254/latest/user-data > /home/ubuntu/user-data-copy.sh

AWS_REGION="$(curl --silent http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region)"

# install docker if it is not installed
if [ ! -x "$(command -v docker)" ]; then
    apt install -y docker-ce docker-ce-cli containerd.io
    usermod -aG docker ubuntu

    # install nvidia container toolkit if we have a nvidia GPU
    if [[ -x "$(command -v nvidia-smi)" ]]; then
        curl -s -L https://nvidia.github.io/nvidia-container-runtime/gpgkey | apt-key add -
        distribution=$(
            . /etc/os-release
            echo $ID$VERSION_ID
        )
        curl -s -L https://nvidia.github.io/nvidia-container-runtime/$distribution/nvidia-container-runtime.list |
            tee /etc/apt/sources.list.d/nvidia-container-runtime.list
        apt-get update
        apt-get -y install nvidia-container-toolkit
    fi
fi

apt install -y tzdata
apt install -y keyboard-configuration
apt install -y gnupg2
apt install -y lsb-core

# install DCV server
echo "install DCV server..."
apt install -y ubuntu-desktop

if [[ $VERSION == "18.04" ]]; then
    echo "Ubuntu 18.04 not supported" && exit 1
elif [[ $VERSION == "20.04" ]]; then
    #bash -c 'echo "deb https://fsx-lustre-client-repo.s3.amazonaws.com/ubuntu focal main" > /etc/apt/sources.list.d/fsxlustreclientrepo.list && apt-get update'

    apt install -y gdm3
    apt -y upgrade
    echo "/usr/sbin/gdm3" >/etc/X11/default-display-manager
    dpkg-reconfigure gdm3
    sed -i -e "s/#WaylandEnable=false/WaylandEnable=false/g" /etc/gdm3/custom.conf
    systemctl restart gdm3

    apt install -y mesa-utils
    if [ -x "$(command -v nvidia-xconfig)" ]; then
        nvidia-xconfig --preserve-busid --enable-all-gpus
    fi

    #restart X server
    echo "restart X-server"
    systemctl set-default graphical.target
    systemctl isolate graphical.target

    wget https://d1uj6qtbmh3dt5.cloudfront.net/2020.2/Servers/nice-dcv-2020.2-9662-ubuntu2004-x86_64.tgz
    tar -xvzf nice-dcv-2020.2-9662-ubuntu2004-x86_64.tgz
    cd nice-dcv-2020.2-9662-ubuntu2004-x86_64 || {
        echo "Failure to cd to extracted directory"
        exit 1
    }
    apt install -y ./nice-dcv-server_2020.2.9662-1_amd64.ubuntu2004.deb/
else
    echo "Ubuntu $VERSION is not supported; must be one of 18.04, or 20.04"
    exit 1
fi

#restart X server
systemctl set-default graphical.target
systemctl isolate graphical.target

# Create DCV server configuration file
mkdir -p /opt/dcv-session-store
(
    cat <<-EOM
[license]
[log]
[session-management]
enable-gl-in-virtual-sessions = true
[session-management/defaults]
[session-management/automatic-console-session]
storage-root="/opt/dcv-session-store/"
[display]
target-fps = 30
quality=(60,90)
max-head-resolution=(4096, 2160)
min-head-resolution=(640, 480)
[connectivity]
idle-timeout=0
enable-quic-frontend=true
[security]
authentication="system"
[clipboard]
primary-selection-copy=true
primary-selection-paste=true
EOM
) >dcv.conf
mv /etc/dcv/dcv.conf "/etc/dcv/dcv.conf-$(date +%Y-%m-%d_%H-%M-%S).bak"
mv dcv.conf /etc/dcv/dcv.conf

# Enable DCV server
systemctl enable dcvserver

# Create DCV session permissions files
rm -f /home/ubuntu/dcv.perms
(
    cat <<-EOM
[permissions]
%owner% allow builtin
EOM
) >/home/ubuntu/dcv.perms


#Create startup session script
(
    cat <<-EOM
#!/bin/bash
dcv create-session --type=console --owner ubuntu --storage-root /opt/dcv-session-store/ --permissions-file /home/ubuntu/dcv.perms dcvsession
EOM
) >/usr/local/bin/start-dcvsession.sh
chmod a+x /usr/local/bin/start-dcvsession.sh

(
    cat <<-EOM
[Unit]
Description=DCV session service
After=dcvserver.service

[Service]
User=root
ExecStart=/usr/local/bin/start-dcvsession.sh
Restart= on-abort

[Install]
WantedBy=graphical.target
EOM
) >/etc/systemd/system/dcvsession.service
systemctl enable dcvsession
echo "install DCV server complete"

# install nfs-common
apt install -y nfs-common

ROS='noetic'
PYTHON=python3

apt install -y python3-minimal python3-pip
test -f /usr/bin/python || ln -s "$(which python3)" /usr/bin/python
pip3 install --upgrade pip
pip3 install boto3
pip3 install kafka-python
pip3 install psycopg2-binary
pip3 install --upgrade awscli
pip3 install jupyterlab

# install ros
echo "install ros $ROS ..."

apt install -y ros-$ROS-desktop-full
echo "source /opt/ros/$ROS/setup.bash" >>/home/ubuntu/.bashrc
apt install -y $PYTHON-rosdep $PYTHON-rosinstall $PYTHON-rosinstall-generator $PYTHON-wstool build-essential

rosdep init || true
rosdep update || true

# Create roscore startup script
(
    cat <<-EOM
#!/bin/bash
source /opt/ros/$ROS/setup.bash
roscore
EOM
) >/usr/local/bin/start-roscore.sh
chmod a+x /usr/local/bin/start-roscore.sh

(
    cat <<-EOM
[Unit]
Description=roscore service

[Service]
User=ubuntu
ExecStart=/usr/local/bin/start-roscore.sh
Restart=on-abort

[Install]
WantedBy=graphical.target
EOM
) >/etc/systemd/system/roscore.service
systemctl enable roscore
echo "install Ros $ROS complete"


# Clone the add-apt-repository
export DIR=/home/ubuntu/amazon-eks-autonomous-driving-data-service
if [ -d "$DIR" ]; then rm -Rf $DIR; fi
cd /home/ubuntu && git clone https://github.com/aws-samples/amazon-eks-autonomous-driving-data-service.git
chown -R ubuntu:ubuntu $DIR

echo "set -o allexport; source /home/ubuntu/.data-service-config; set +o allexport" >> /home/ubuntu/.bashrc


# Update User Password
SECRET_VALUE=$(aws secretsmanager get-secret-value --secret-id "$DATA_SERVICE_USER_SECRET_NAME" --query SecretString --output text --region "$AWS_REGION" | jq -r)
TARGET_USERNAME=ubuntu
NEW_PASSWORD=$(echo "${SECRET_VALUE}" | jq -r '.password')


echo "$TARGET_USERNAME:$NEW_PASSWORD" | chpasswd


# Create config file
mkdir /home/ubuntu/.aws
cat >/home/ubuntu/.aws/config <<EOL
[default]
region = ${AWS_REGION}
output=json

EOL
chown -R ubuntu:ubuntu /home/ubuntu/.aws

# Install Foxglove
export foxglove=1.29.0
mkdir -p /tmp/foxglove
wget https://github.com/foxglove/studio/releases/download/v${foxglove}/foxglove-studio-${foxglove}-linux-amd64.deb -O /tmp/foxglove/foxglove-studio-${foxglove}-linux-amd64.deb
apt install -y --allow-downgrades /tmp/foxglove/foxglove-studio-${foxglove}-linux-amd64.deb
rm -rf /tmp/foxglove

# Install Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - 
sh -c 'echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt install ./google-chrome-stable_current_amd64.deb
rm -f google-chrome-stable_current_amd64.deb




export kubectl_version=1.11.9/2019-03-27
# install kubectl for EKS
mkdir -p /usr/local/bin
curl -o /usr/local/bin/kubectl "https://amazon-eks.s3.us-west-2.amazonaws.com/${kubectl_version}/bin/linux/amd64/kubectl"
chmod a+x /usr/local/bin/kubectl
curl -o /usr/local/bin/aws-iam-authenticator "https://amazon-eks.s3.us-west-2.amazonaws.com/${kubectl_version}/bin/linux/amd64/aws-iam-authenticator"

# install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
mv /tmp/eksctl /usr/local/bin

# install helm
curl -o /tmp/get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
chmod 700 /tmp/get_helm.sh
/tmp/get_helm.sh
rm /tmp/get_helm.sh

# Copy onto the ubuntu home dir any staged scripts
aws s3 cp s3://$S3_SCRIPT_BUCKET/$SCRIPT_PATH /home/$TARGET_USERNAME/scripts --recursive || true
chown ubuntu:ubuntu /home/$TARGET_USERNAME/scripts -R || true

echo "NICE DCV server is enabled!" >/etc/motd

if [ ! -f /home/ubuntu/.rebooted ]; then
	echo "First Time rebooting"
    touch /home/ubuntu/.rebooted
    reboot
fi

