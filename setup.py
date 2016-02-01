from setuptools import setup

setup(
    name='tattle',
    version='0.1.6',
    packages=[
        'tattle',
    ],
    url='https://github.com/cloudify-cosmo/tattle',
    author='Gigaspaces',
    author_email='cosmo-admin@gigaspaces.com',
    entry_points={
        'console_scripts': [
            'tattle = tattle.engine:main',
        ]
    },
    install_requires=[
        'requests>=2.7.0',
        'pyyaml>=3.10'
    ],
)
