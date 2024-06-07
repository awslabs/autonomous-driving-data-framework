set -eux

nvidia-smi

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

mkdir -p /opt/health-check
touch /opt/health-check/ready

while true
do
  echo "Checking for input"
  # Receive a message from the SQS queue
  message=$(aws sqs receive-message --queue-url "${EUREKA_TRAINING_QUEUE_URL}" --max-number-of-messages 1 --visibility-timeout 30 --query 'Messages[0]')

  # Check if a message was received
  if [ "$message" != "null" ]; then
    # Extract the message receipt handle
    receipt_handle=$(echo $message | jq -r '.ReceiptHandle')

    # Process the message (replace this with your actual processing logic)
    echo "Processing message: $(echo $message | jq -r '.Body')"

    # Delete the message from the SQS queue
    aws sqs delete-message --queue-url "${EUREKA_TRAINING_QUEUE_URL}" --receipt-handle "$receipt_handle"
    input_file=$(echo $message | jq -r '.Body')
    cp "$input_file" /tmp/task.env
    break
  else
      echo "No messages in the queue."
  fi
  sleep 10
done

source /tmp/task.env
cd "${EUREKA_WORKING_DIR}"

#set +e
${EUREKA_CMD} 2>&1 | tee "$EUREKA_LOG_PATH"
if [[ -z "${EUREKA_CLEANUP}" ]]; then
  "${EUREKA_CLEANUP}"
fi

rm -rf "$input_file"

# Check the return code
#if [ $? -eq 0 ]; then
#  echo "Training successful"
#  rm -rf "$input_file"
#else
#  aws sqs send-message --queue-url "$EUREKA_TRAINING_QUEUE_URL" --message-body "$input_file"
#  echo "Training error. Putting task back to queue."
#  exit 1
#fi