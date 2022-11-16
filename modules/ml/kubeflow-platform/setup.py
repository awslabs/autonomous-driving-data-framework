import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    version="0.1.0",
    description="Kubeflow via kubeflow-on-aws - https://awslabs.github.io/kubeflow-manifests/docs/",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="author",
    install_requires=[
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Typing :: Typed",
    ],
)
