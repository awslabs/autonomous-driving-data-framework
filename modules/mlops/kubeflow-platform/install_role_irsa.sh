#!/bin/bash

export DEP_MOD=${AWS_CODESEEDER_NAME}-${ADDF_DEPLOYMENT_NAME}-${ADDF_MODULE_NAME}-${AWS_DEFAULT_REGION}
export POLICY_NAME=${DEP_MOD}-policy
export SA_ROLE_NAME=${DEP_MOD}-sa-role
export SA_NAME=profiles-controller-service-account
export SA_ANNOTATION=$(kubectl get sa ${SA_NAME} -n kubeflow -o json | jq ".metadata.annotations" | grep "eks.amazonaws.com/role-arn")
if [[ ! "$SA_ANNOTATION" ]]; then
    sed -i -e "s/AWS_ACCOUNT_ID/${AWS_ACCOUNT_ID}/g" policies/iam-profile-sa-policy.json
    sed -i -e "s/ADDF_DEPLOYMENT_NAME/${ADDF_DEPLOYMENT_NAME}/g" policies/iam-profile-sa-policy.json 
    aws iam get-policy --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME:0:60} || \
    aws iam create-policy --policy-name ${POLICY_NAME:0:60} --policy-document file://policies/iam-profile-sa-policy.json;
    eksctl delete iamserviceaccount --name ${SA_NAME} --namespace kubeflow --cluster ${ADDF_PARAMETER_EKS_CLUSTER_NAME} || true;
    eksctl create iamserviceaccount --name ${SA_NAME} --namespace kubeflow \
    --cluster ${ADDF_PARAMETER_EKS_CLUSTER_NAME} --role-name ${SA_ROLE_NAME:0:60} \
    --attach-policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME:0:60} \
    --override-existing-serviceaccounts --approve;
    kubectl rollout restart deployment profiles-deployment -n kubeflow;
fi