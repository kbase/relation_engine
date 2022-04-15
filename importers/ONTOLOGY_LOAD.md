# Loading ontology procedure

#### Downloading obo file.
* Ex. PO obo was downloaded from http://purl.obolibrary.org/obo/po.obo

#### Converting obo to obograph.
* Cloning https://github.com/ontodev/robot
* Running it do conversion, Ex.

```sh
docker run -v `pwd`:`pwd` --user $(id -u) -w `pwd` robot convert \
--input ~/tmp/gaz.obo --output ~/tmp/gaz.json
```

#### Running scripts/prepare_ontology.py to generate yaml files for ontology
```sh
python3 scripts/prepare_ontology.py scripts/test/data/data_sources.json po_ontology
```

#### Preparing PR with generated ontology yaml files and requesting for merge and deployment
* Corresponding collections should be created in arango

#### Preparing relation_engine_importers
* Cloning https://github.com/kbase/relation_engine_importers
* setup ssh tunnel for arangodb

#### Loading with obograph_delta_loader.py
```sh
relation_engine/ontologies/obograph/loaders/obograph_delta_loader.py \
--file ~/package/plant-ontology/po.json --onto-id-prefix PO \
--arango-url http://127.0.0.1:48000/ --database luj_test --load-namespace po_ontology \
--node-collection PO_terms --edge-collection PO_edges --merge-edge-collection PO_merges \
--load-version release_999 --load-registry-collection delta_load_registry \
--load-timestamp $(( $(date '+%s%N') / 1000000)) --release-timestamp $(( $(date '+%s%N') / 1000000)) \
--user $USER --pwd-file passfile --graph-id "http://purl.obolibrary.org/obo/po.owl"
```
* The passfile contains user's arango password.
* The “--graph-id” is required if there are more than one graphs in obograph file.
