## Test Spec Release

`sample_spec_release`, and the corresponding archive, `spec.tar.gz`, contain a set of sample schema files suitable for use in tests.

To create a new version of `spec.tar.gz`, you will need to exec into the `re_api` docker image to ensure that the new archive and its contents have the appropriate file owner and permissions (all files must have owner and group `root`/`root`).

Example commands:

```
$ docker exec -it relation_engine_re_api_run_1234567890 sh
# # in the docker image
# cd relation_engine_server/test/spec_release
# # ... perform any edits ...
# tar -czvf new_spec.tar.gz sample_spec_release/
# # check the file listing is as expected
# tar -ztvf new_spec.tar.gz
# mv spec.tar.gz old_spec.tar.gz
# mv new_spec.tar.gz spec.tar.gz
# # ensure that the tests pass
# cd /app
# sh scripts/run_tests.sh
```
