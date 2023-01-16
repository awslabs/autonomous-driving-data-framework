## Sample Use Case

This project contains a sample MLOPS solution including infrastructure as code and sample notebooks and sagemaker pipeline.

## Deployment

To deploy your new use case, follow the steps:

1. Open SageMaker Studio.
2. Start new SageMaker project from project template
3. Open terminal
4. Using terminal command `cd` go to the repository that you cloned in the step before
5. Run `sh boostrap.sh` and enter the data when the prompt asks you
6. Run `sh deploy.sh`. At some point, the script will print out number of resources to deploy and ask for confirmation. Confirm by entering `y`
   From that point onwards, all the changes to SageMaker stable pipeline inside repository main branch will be automatically deployed.
7. Optional: Subscribe to SNS topic prefixed with your project name

### Project Structure

```
├── bootstrap.sh   <--- Run on first Init
├── buildspec.yaml <--- CICD Build Specification
├── deploy.sh      <--- Deploy infrastructure as Code
├── infra          <--- Infrastructure as Code (CDK) App
│   ├── app.py     <--- CDK App
│   ├── pipeline.py
│   ├── source-activate-venv <--- Activate Node & Python virtual envs
└── ml              <--- Machine Learning Code
    ├── requirements.txt
    ├── scripts                 <-- Scripts for pipeline steps
    │   ├── __init__.py
    │   ├── evaluate.py
    │   └── preprocess.py
    └── stable_pipeline.py      <-- Stable pipeline code
```