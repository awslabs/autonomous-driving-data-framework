set -ex

aws sqs purge-queue --queue-url "$EUREKA_TRAINING_QUEUE_URL"

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
conda activate eureka
cp /opt/python_env/anaconda3/envs/eureka/lib/libpython3.8.so.1.0 /usr/lib

cd /mnt/fsx/ns1/addf-dcv-demo-us-east-2/Eureka/eureka
mkdir -p env_files
#python eureka.py env=shadow_hand sample=4 iteration=2 model=gpt-4
python eureka_distributed.py \
    env="${EUREKA_ENV}" \
    sample="${EUREKA_SAMPLE}" \
    iteration="${EUREKA_ITERATIONS}" \
    model="${EUREKA_MODEL}" \
    max_iterations="${EUREKA_MAX_ITERATION}" \
    num_eval="${EUREKA_NUM_EVAL}"

set +x
while true
do
  sleep 5
done
