from setuptools import setup, find_packages


setup(
    name='relation_engine_api',
    version='0.0.1',
    description='Relation Engine API',
    author_email='info@kbase.us',
    url='',
    install_requires=[
        'connexion'
    ],
    packages=find_packages(),
    package_data={'': ['src/relation_engine_api/openapi/api_v1.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['swagger_server=relation_engine_api.__main__:main']
    },
    long_description='Relation Engine Rest/JSON API.'''
)
