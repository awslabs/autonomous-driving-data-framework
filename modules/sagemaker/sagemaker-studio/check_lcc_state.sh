CURRENT_LLC_CONTENT=$(aws sagemaker describe-studio-lifecycle-config --studio-lifecycle-config-name $ADDF_PARAMETER_SERVER_LIFECYCLE_NAME | jq -r ."StudioLifecycleConfigContent")

if [ "$CURRENT_LLC_CONTENT" != "$LCC_CONTENT" ]; then
    echo "Lifecycle configuration content needs to be updated, but lifecycle config $ADDF_PARAMETER_SERVER_LIFECYCLE_NAME already exists. Please manually remove the SageMaker studio LCC with name $ADDF_PARAMETER_SERVER_LIFECYCLE_NAME or name the configuration differently"
    exit 1
fi