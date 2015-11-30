from setuptools import setup

setup(
    name='tattle',
    version='0.1.0',
    packages=[
        'tattle',
    ],
    url='https://github.com/cloudify-cosmo/tattle',
    author='Gigaspaces',
    author_email='cosmo-admin@gigaspaces.com',
    install_requires=[
        'requests>=2.7.0',
        'pyyaml>=3.11'
    ],
)
