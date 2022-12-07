import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    version="0.1.0",
    description="This module deploys an EC2 istnaces with Ubuntu Desktop, Foxglove, and Rviz with access via NiceDCV",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="author",
    install_requires=[
        "aws-cdk-lib==2.20.0",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Typing :: Typed",
    ],
)
