from distutils.core import setup


setup(
    name='releng-client',
    version='0.0.1',
    description='KBase Relation Engine API Client Module',
    author='KBase Team',
    url='https://github.com/kbase/relation_engine_api',
    packages=['relation_engine_client'],
    package_dir={'': 'src'},
    install_requires=['requests>=2'],
)
