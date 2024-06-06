curl -O https://repo.anaconda.com/archive/Anaconda3-2024.02-1-Linux-x86_64.sh
chmod +x ./Anaconda3-2024.02-1-Linux-x86_64.sh
rm -rf /opt/python_env/anaconda3
bash ./Anaconda3-2024.02-1-Linux-x86_64.sh -b -p /opt/python_env/anaconda3

__conda_setup="$('/opt/python_env/anaconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/python_env/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/opt/python_env/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/opt/python_env/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup

conda init bash
conda create -n eureka python=3.8 -y
conda activate eureka
cp /opt/python_env/anaconda3/envs/eureka/lib/libpython3.8.so.1.0 /usr/lib

cd /mnt/fsx/ns1/addf-dcv-demo-us-east-2/isaacgym/python
pip install -e .

cd /mnt/fsx/ns1/addf-dcv-demo-us-east-2/Eureka
pip install -e .
cd isaacgymenvs; pip install -e .
cd ../rl_games; pip install -e .
pip install xvfbwrapper ipython progressbar2

cp -r /mnt/fsx/ns1/addf-dcv-demo-us-east-2/fbx /opt/python_env/anaconda3/envs/eureka/lib/python3.8/site-packages/
cp /mnt/fsx/ns1/addf-dcv-demo-us-east-2/FbxCommon.py /opt/python_env/anaconda3/envs/eureka/lib/python3.8/site-packages/

mkdir /opt/health-check
touch /opt/health-check/ready
echo "Setup done..."

set +x
while true
do
  sleep 5
done
