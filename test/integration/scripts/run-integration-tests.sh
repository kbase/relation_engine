set -e
echo "Starting RE_API checker:"
python -m test.integration.utils.wait_for_re_api
echo 'RE_API available!'
echo "Running Integration Tests:"
python -m unittest discover test/integration/tests
