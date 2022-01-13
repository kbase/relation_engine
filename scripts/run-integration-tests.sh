# Sets up and runs integration tests.
export INTEGRATION_TEST_DATA_DIR=`pwd`/test/integration/data
cd test/integration
docker-compose run --rm testrunner
cd ../..