[![Total alerts](https://img.shields.io/lgtm/alerts/g/kbase/relation_engine.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/kbase/relation_engine/alerts/) [![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/kbase/relation_engine.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/kbase/relation_engine/context:python)
![RE test and deploy](https://github.com/kbase/relation_engine/workflows/Relation%20Engine%20test%20and%20deploy/badge.svg)

# KBase Relation Engine

This repo holds the code associated with the KBase relation engine, previously held in https://github.com/kbase/relation_engine_api and https://github.com/kbase/relation_engine_spec.

## Relation Engine Spec
### `spec/`

The `spec/` directory holds the schemas for [stored queries](spec/stored_queries), [collections](spec/collections), [views](spec/views), [analyzers](spec/analyzers), and [migrations](spec/migrations) for the relation engine graph database service.

These specifications are used by the [Relation Engine API](relation_engine_server).

## Relation Engine API
### `relation_engine_server/`

The relation engine server (`relation_engine_server/`) is a simple API that allows KBase community developers to interact with the Relation Engine graph database. You can run stored queries or do bulk updates on documents.

## Relation Engine Startup
* Docker image is built with environment variable `SPEC_RELEASE_PATH=/opt/spec.tar.gz`. This contains the specs from the repo itself.
* Wait for response from auth, workspace, and arangodb services, as they are set up
* Specs are set up. Either the repo specs or remote specs are loaded into the specs root path
* Collections, views, and analyzers from the specs are added to the ArangoDB server. If the collection, view, or analyzer already exists, but in a different configuration, it will _not_ be overwritten.
* Collections, views, and analyzers from the loaded specs are compared to those on the ArangoDB server. If the loaded specs' attributes are not recursively a subset of the server specs, then an exception is raise. (This is just preliminary validation behavior.)


## Relation Engine builds

The Relation Engine is available on github packages. These images are built by the configs in the .github repo.
The develop tags are located at https://github.com/kbase/relation_engine/pkgs/container/relation_engine-develop  
e.g.
```
docker pull ghcr.io/kbase/relation_engine-develop:latest (Built upon merging a PR)
docker pull ghcr.io/kbase/relation_engine-develop:pr-93 (Built upon creating a PR)
```

## How to Deploy in CI
The CI service is available in the `relationapi` service
* Press Upgrade Arrow
* Ensure the relationapi service uses `ghcr.io/kbase/relation_engine-develop:latest`
* Ensure the `Always pull image before creating` box is ticked
* Press `Upgrade` button
* If the deployment suceeded, you can finish the upgrade. If not, you can press the rollback button.

(For deployments to other environments, request help from the #devops channel)

## How to Deploy to production
* Merge from Develop to Main
* Draft a release using semantic versioning (e.g 1.2.3) by creating a tag with the target of Main
* Ensure release notes are updated manually and/or by AutoGenerate Release Notes
