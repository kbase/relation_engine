## Test Spec Release

`sample_spec_release`, and the corresponding archive, `spec.tar.gz`, contain a set of sample schema files suitable for use in tests.

To create a new version of `spec.tar.gz`, you will need to open a shell into the `re_api` docker image and create the new archive there to ensure that the new archive and its contents have the appropriate file owner and permissions (all files must have owner and group `root`/`root`).

Ensure that you have mounted your current working directory as `/app` in the docker `re_api` image by uncommenting the lines in `docker-compose.yaml`:

``` yaml
  re_api:
    ( ... )
#    uncomment to mount local directories
    volumes:
      - ${PWD}:/app
```

Run `make shell` to start up the docker container, and then get the ID of the current `re_api` image. Exec into the `re_api` image via the Docker Desktop client or the command line:

``` sh
$ docker exec -it relation_engine_re_api_run_1234567890 sh
```

Example commands for updating `spec.tar.gz`:

``` sh
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
