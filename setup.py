from setuptools import setup

setup(
    name='cloudify-repo-status',
    version='0.1',
    packages=[
        'repo_status',
    ],
    install_requires=[
        'requests>=2.7.0'
    ],
)
