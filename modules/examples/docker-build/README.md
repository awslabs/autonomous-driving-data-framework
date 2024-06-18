# Introduction

## Description

This module demonstrates an example on how to build Docker Images from a given source, then pushes to AWS ECR, where the image vulnerability scanning happens on every image push.

### Required Parameters

- `ecr-repo-name`: ECR Repository name to be used/created if it doesn't exist.
