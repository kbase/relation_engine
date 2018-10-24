from setuptools import setup, find_packages

setup(
    name='relation_engine_spec',
    version='0.1',
    author='Jay Bolton',
    author_email='jrbolton@lbl.gov',
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['*.aql', '*.json']},
    license='MIT',
    description='Specifications for the KBase Relation Engine API.',
    url='https://kbase.us',
    python_requires='>=3',
    install_requires=[
        'jsonschema'
    ]
)
