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

#!/bin/bash -x
echo "Cloud init in progress. Machine will REBOOT after cloud init is complete!!" > /etc/motd
export DEBIAN_FRONTEND=noninteractive
export DEBCONF_NONINTERACTIVE_SEEN=true

# External Variables
SERVICE_USER_SECRET_NAME="PLACEHOLDER_SECRET"
S3_BUCKET_NAME="PLACEHOLDER_S3_BUCKET_NAME"
SCRIPTS_PATH="PLACEHOLDER_SCRIPTS_PATH"

# Other variables
[[ ! -x "$(command -v lsb_release)" ]] && (echo "Check if the system is Ubuntu" && exit 1) || echo "CHECK: System is Ubuntu based, continuing with install"
VERSION=$(lsb_release -a | grep Release | awk -F ":" '{print $2}' | sed -E -e 's/[[:blank:]]+//g')
RELEASE=$(lsb_release -sc)
DEF_ARCH="amd64" # We assume we are in an x86_64 system
PLATFORM="$(uname -s)_${DEF_ARCH}"
IMDSV2_TOKEN=$(curl --silent -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
AWS_REGION="$(curl --silent -H "X-aws-ec2-metadata-token: ${IMDSV2_TOKEN}" http://169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region)"
NICE_DCV_BASE="https://d1uj6qtbmh3dt5.cloudfront.net/2023.1/Servers"
ROS_PKG_PREFIX="python3"
PYTHON_VERSION="python3.11"
ADDS_REPO="amazon-eks-autonomous-driving-data-service"
KUBECTL_VERSION="1.29.3/2024-04-19"
FOXBOX_VERSION="1.0.0"
FOXBOX_FILE="foxbox-${FOXBOX_VERSION}-linux-${DEF_ARCH}.deb"
case "${VERSION}" in
  "20.04")
    NVIDIA_UBUNTU_BASE="ubuntu2004/x86_64"
    NVIDIA_PIN_FILE="cuda-ubuntu2004.pin"
    ROS_VERSION="noetic"
    ROS_BASE="ros"
    NICE_DCV_VERSION="nice-dcv-2023.1-16388-ubuntu2004-x86_64.tgz"
  ;;
  "22.04")
    NVIDIA_UBUNTU_BASE="ubuntu2204/x86_64"
    NVIDIA_PIN_FILE="cuda-ubuntu2204.pin"
    ROS_VERSION="humble"
    ROS_BASE="ros2"
    NICE_DCV_VERSION="nice-dcv-2023.1-16388-ubuntu2204-x86_64.tgz"
  ;;
  "18.04")
    echo "Ubuntu 18.04 is not supported. Please select another version" && exit 1
  ;;
  *)
    echo "Not recognized version: ${VERSION}" && exit 1
  ;;
esac

# Functions
get_file() {
  wget -t0 -c "${1}"
}

detect_nvidia() {
  [[ ! -x "$(command -v nvidia-smi)" ]] &&
  [[ -n "$(ubuntu-drivers devices 2>/dev/null | grep nvidia-driver | grep recommended | awk -F " " '{print $3}')" ]] &&
  echo "true" || echo "false"
}

install_nvidia_drivers() {
  # Install NVIDIA Repositories and latest drivers
  NVIDIA_UBUNTU_BASE=$1
  NVIDIA_PIN_FILE=$2
  BASE_URL="https://developer.download.nvidia.com/compute/cuda/repos/${NVIDIA_UBUNTU_BASE}"
  get_file "${BASE_URL}/${NVIDIA_PIN_FILE}" &&
  mv "${NVIDIA_PIN_FILE}" /etc/apt/preferences.d/cuda-repository-pin-600 &&
  apt-key adv --fetch-keys "${BASE_URL}/3bf863cc.pub" &&
  add-apt-repository "deb ${BASE_URL}/ /" &&
  apt-get update && apt-get -y purge cuda && apt-get -y purge nvidia-* && apt-get -y autoremove &&
  ubuntu-drivers autoinstall &&
  apt-get -y install cuda nvidia-cuda-toolkit libcudnn8 libcudnn8-dev;
}

# Start execution 
echo "Detected Ubuntu ${VERSION}"

# Store user-data script
echo "Saving user-data script in the ubuntu user's home directory"
curl -H "X-aws-ec2-metadata-token: ${IMDSV2_TOKEN}" http://169.254.169.254/latest/user-data > /home/ubuntu/user-data-copy.sh

# Install and update latest base packages
apt-get update && apt-get -y upgrade
apt-get -y install ubuntu-drivers-common \
  "linux-headers-$(uname -r)" \
  git tar apt-transport-https ca-certificates curl jq gnupg-agent software-properties-common \
  tzdata gnupg2 lsb-core build-essential

# Install NVIDIA Drivers if needed
if [[ $(detect_nvidia) == "true" ]]; then
  install_nvidia_drivers "${NVIDIA_UBUNTU_BASE}" "${NVIDIA_PIN_FILE}"
  echo "Rebooting instance for drivers to be loaded properly"
  reboot
fi

# Setup Repositories
## Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
apt-key fingerprint 0EBFCD88
add-apt-repository "deb [arch=${DEF_ARCH}] https://download.docker.com/linux/ubuntu ${RELEASE} stable"

## FSx Lustre
wget -c -O - https://fsx-lustre-client-repo-public-keys.s3.amazonaws.com/fsx-ubuntu-public-key.asc | apt-key add -

## NiceDCV
get_file https://d1uj6qtbmh3dt5.cloudfront.net/NICE-GPG-KEY
gpg --import NICE-GPG-KEY
get_file "${NICE_DCV_BASE}/${NICE_DCV_VERSION}"

## ROS
echo "deb http://packages.ros.org/${ROS_BASE}/ubuntu ${RELEASE} main" > /etc/apt/sources.list.d/ros-latest.list
apt-key adv --keyserver 'hkp://keyserver.ubuntu.com:80' --recv-key C1CF6E31E6BADE8868B172B4F42ED6FBAB17C654

## Python 3.11
add-apt-repository ppa:deadsnakes/ppa -y

## Chrome
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
sh -c 'echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
wget -q -t0 -c "https://dl.google.com/linux/direct/google-chrome-${DEF_ARCH}.deb" -O ./google-chrome.deb
apt-get install -y ./google-chrome.deb

## NVIDIA Container Runtime
NVIDIA_BASE="https://nvidia.github.io/libnvidia-container"
curl -fsSL "${NVIDIA_BASE}/gpgkey" | gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg &&
curl -s -L "${NVIDIA_BASE}/stable/deb/nvidia-container-toolkit.list" | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

## FoxBox
get_file "https://github.com/bmw-software-engineering/foxbox/releases/download/${FOXBOX_VERSION}/${FOXBOX_FILE}"

# Update recently added sources
apt-get update

# Install GUI and other needed packages
apt-get install -y keyboard-configuration ubuntu-desktop gdm3 \
  mesa-utils nfs-common "${PYTHON_VERSION}" "${PYTHON_VERSION}-venv" \
  docker-ce docker-ce-cli containerd.io nvidia-container-toolkit

# Python 3.11 (PIP)
test -f /usr/bin/python || ln -s "$(command -v ${PYTHON_VERSION})" /usr/bin/python
get_file https://bootstrap.pypa.io/get-pip.py
python ./get-pip.py

if [[ -x "$(command -v pip3)" ]] ; then
  pip3 install --upgrade pip awscli
  pip3 install boto3 kafka-python psycopg2-binary jupyterlab
fi 

# Check for missing upgrades
apt-get upgrade -y

# Configure GUI
case "${VERSION}" in
  "20.04" | "22.04")
    if [[ -x "$(command -v gdm3)" ]]; then
      echo "/usr/sbin/gdm3" >/etc/X11/default-display-manager
      dpkg-reconfigure gdm3
      sed -i -e "s/#WaylandEnable=false/WaylandEnable=false/g" /etc/gdm3/custom.conf
      systemctl restart gdm3
    fi
    if [[ -x "$(command -v nvidia-xconfig)" ]]; then
      nvidia-xconfig --preserve-busid --enable-all-gpus
    fi
  ;;
esac

# Install NiceDCV
if [[ -f "${NICE_DCV_VERSION}" ]]; then
  mkdir -p nice_dcv /opt/dcv-session-store
  tar -xf "${NICE_DCV_VERSION}" -C nice_dcv
  NICE_DCV_DEB=$(find nice_dcv -name "nice-dcv-server*.deb")
  apt-get install -y "./${NICE_DCV_DEB}"
  # Create configuration file
  mv /etc/dcv/dcv.conf "/etc/dcv/dcv.conf-$(date +%Y-%m-%d_%H-%M-%S).bak"
  printf '%s\n' \
    "[license]" \
    "[log]" \
    "[session-management]" \
    "enable-gl-in-virtual-sessions = true" \
    "[session-management/defaults]" \
    "[session-management/automatic-console-session]" \
    "storage-root=\"/opt/dcv-session-store/\"" \
    "[display]" \
    "target-fps = 30" \
    "quality=(60,90)" \
    "max-head-resolution=(4096, 2160)" \
    "min-head-resolution=(640, 480)" \
    "[connectivity]" \
    "idle-timeout=0" \
    "enable-quic-frontend=true" \
    "[security]" \
    "authentication=\"system\"" \
    "[clipboard]" \
    "primary-selection-copy=true" \
    "primary-selection-paste=true" > /etc/dcv/dcv.conf
  # Enable DCV server
  systemctl enable dcvserver

  [[ -f "/home/ubuntu/dcv.perms" ]] && rm -f /home/ubuntu/dcv.perms
  printf '%s\n' \
    "[permissions]" \
    "%owner% allow builtin" > /home/ubuntu/dcv.perms

  [[ -f "/usr/local/bin/start-dcvsession.sh" ]] && rm -f /usr/local/bin/start-dcvsession.sh
  printf '%s\n' \
    "#!/bin/bash" \
    "dcv create-session \
      --type=console \
      --owner ubuntu \
      --storage-root /opt/dcv-session-store/ \
      --permissions-file /home/ubuntu/dcv.perms dcvsession" > /usr/local/bin/start-dcvsession.sh
  chmod a+x /usr/local/bin/start-dcvsession.sh
  
  [[ -f "/etc/systemd/system/dcvsession.service" ]] && rm -f /etc/systemd/system/dcvsession.service
  printf '%s\n' \
    "[Unit]" \
    "Description=DCV session service" \
    "After=dcvserver.service" \
    "" \
    "[Service]" \
    "User=root" \
    "ExecStart=/usr/local/bin/start-dcvsession.sh" \
    "Restart= on-abort" \
    "" \
    "[Install]" \
    "WantedBy=graphical.target" > /etc/systemd/system/dcvsession.service

  systemctl enable dcvsession
  # Restart X-Server
  systemctl set-default graphical.target
  systemctl isolate graphical.target

  echo "DCV server installation complete"
fi

# ROS Installation
if [[ ! -x "$(command -v rosdep)" ]]; then
  echo "Installing ROS = ${ROS_VERSION} ..."
  apt-get install -y "ros-${ROS_VERSION}-desktop-full" \
    "${ROS_PKG_PREFIX}-rosdep" \
    "${ROS_PKG_PREFIX}-rosinstall" \
    "${ROS_PKG_PREFIX}-rosinstall-generator" \
    "${ROS_PKG_PREFIX}-wstool"
  sed -i '/^#===ROS_CONFIG/,/^#===END_ROS_CONFIG/d' "/home/ubuntu/.bashrc"
  {
    echo "#===ROS_CONFIG==="
    echo "source /opt/ros/${ROS_VERSION}/setup.bash"
    echo "#===END_ROS_CONFIG==="
  } >> /home/ubuntu/.bashrc

  rosdep init || true
  rosdep update || true

  # Create roscore startup script
  [[ -f "/usr/local/bin/start-roscore.sh" ]] && rm -f /usr/local/bin/start-roscore.sh
  printf '%s\n' \
    "#!/bin/bash" \
    "source /opt/ros/$ROS/setup.bash" \
    "roscore" > /usr/local/bin/start-roscore.sh
  chmod a+x /usr/local/bin/start-roscore.sh

  [[ -f "/etc/systemd/system/roscore.service" ]] && rm -f /etc/systemd/system/roscore.service
  printf '%s\n' \
    "[Unit]" \
    "Description=roscore service" \
    "" \
    "[Service]" \
    "User=ubuntu" \
    "ExecStart=/usr/local/bin/start-roscore.sh" \
    "Restart=on-abort" \
    "" \
    "[Install]" \
    "WantedBy=graphical.target" > /etc/systemd/system/roscore.service
  systemctl enable roscore
  echo "ROS ${ROS_VERSION} installation complete."
fi

# Install KubeCTL for EKS, EKSCTL and Helm3
[[ ! -d "/usr/local/bin" ]] && mkdir -p /usr/local/bin
curl -sL -o /usr/local/bin/kubectl "https://s3.us-west-2.amazonaws.com/amazon-eks/${KUBECTL_VERSION}/bin/linux/${DEF_ARCH}/kubectl"
curl -sL -o /usr/local/bin/aws-iam-authenticator "https://s3.us-west-2.amazonaws.com/amazon-eks/${KUBECTL_VERSION}/bin/linux/${DEF_ARCH}/aws-iam-authenticator"
curl -sL "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_${PLATFORM}.tar.gz" | tar xz -C /tmp
mv /tmp/eksctl /usr/local/bin
chmod a+x /usr/local/bin/kubectl /usr/local/bin/aws-iam-authenticator /usr/local/bin/eksctl
curl -sL -o /tmp/get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
chmod u+x /tmp/get_helm.sh
/tmp/get_helm.sh

# Install FoxBox
apt-get install -y "./${FOXBOX_FILE}"

# Installing ADDS Repository
[[ -d "/home/ubuntu/${ADDS_REPO}" ]] && rm -Rf "/home/ubuntu/${ADDS_REPO}"
git clone "https://github.com/aws-samples/${ADDS_REPO}.git" "/home/ubuntu/${ADDS_REPO}"
chown -R ubuntu:ubuntu "/home/ubuntu/${ADDS_REPO}"

sed -i '/^#===DATA_SERV_CONFIG/,/^#===END_DATA_SERV_CONFIG/d' "/home/ubuntu/.bashrc"
{
  echo "#===DATA_SERV_CONFIG==="
  echo 'DATA_SERV_FILE="/home/ubuntu/.data-service-config"'
  echo '[[ -f "${DATA_SERV_FILE}" ]] && (set -o allexport; source "${DATA_SERV_FILE}"; set +o allexport)'
  echo "#===END_DATA_SERV_CONFIG==="
} >> /home/ubuntu/.bashrc

# Copy Staged scripts
if [[ "${S3_BUCKET_NAME}" != "PLACEHOLDER_S3_BUCKET_NAME" ]] && [[ "${SCRIPTS_PATH}" != "PLACEHOLDER_SCRIPTS_PATH" ]]; then
  mkdir -p /home/ubuntu/scripts
  aws s3 cp "s3://${S3_BUCKET_NAME}/${SCRIPTS_PATH}" /home/ubuntu/scripts/ --recursive
  chown -R ubuntu:ubuntu /home/ubuntu/scripts
fi

# Get Secret Value to set ubuntu's user password
if [[ "${SERVICE_USER_SECRET_NAME}" != "PLACEHOLDER_SECRET" ]]; then
  SECRET_VALUE=$(aws secretsmanager get-secret-value --secret-id "${SERVICE_USER_SECRET_NAME}" --query SecretString --output text --region "${AWS_REGION}" | jq -r)
  NEW_PASSWORD=$(echo "${SECRET_VALUE}" | jq -r '.password')
  echo "ubuntu:${NEW_PASSWORD}" | chpasswd
fi

# Avoid initial setup that ask for upgrade
[[ ! -d "/home/ubuntu/.config" ]] && mkdir -p /home/ubuntu/.config
echo "yes" >> /home/ubuntu/.config/gnome-initial-setup-done

# Last reboot
if [[ ! -f "/home/ubuntu/.rebooted" ]]; then
  echo "NICE DCV server is enabled!" > /etc/motd
	echo "Rebooting after all configurations"
  touch /home/ubuntu/.rebooted
  reboot
fi