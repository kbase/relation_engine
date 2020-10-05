"""
Loads the Dan Jacobson/ORNL group's gene and phenotype network data into arangodb.

Running this requires a set of source files provided by the ORNL group.

The parser sets up its configuration, including the files it will parse, from the RES_ROOT_DATA_PATH
environment variable once per instantiation. To parse a set of files from a different directory,
create a new parser with RES_ROOT_DATA_PATH set appropriately.

Sample usage:

from the command line:

# load files from /path/to/data/dir
RES_ROOT_DATA_PATH=/path/to/data/dir python -m importers.djornl.parser

"""
import json
import requests
import os
import csv
import yaml

import importers.utils.config as config
from relation_engine_server.utils.json_validation import run_validator, get_schema_validator


class DJORNL_Parser(object):

    def config(self, value):
        if not hasattr(self, '_config'):
            self._configure()

        if value not in self._config:
            raise KeyError(f'No such config value: {value}')

        return self._config[value]

    def _configure(self):

        configuration = config.load_from_env(extra_required=['ROOT_DATA_PATH'])

        # Collection name config
        configuration['node_name'] = 'djornl_node'
        configuration['edge_name'] = 'djornl_edge'

        # fetch the manifest and make sure all the files listed actually exist
        manifest = self._get_manifest(configuration)
        for type in ['node', 'edge', 'cluster']:
            configuration[type + '_files'] = []

        error_list = []
        for file in manifest['file_list']:
            file_path = os.path.join(configuration['ROOT_DATA_PATH'], file['path'])

            if not os.path.exists(file_path):
                error_list.append(f"{file_path}: file does not exist")
                continue

            if not os.path.isfile(file_path):
                error_list.append(f"{file_path}: not a file")
                continue

            # add the file to the appropriate list
            file['file_path'] = file_path
            configuration[file['data_type'] + '_files'].append(file)

        if error_list:
            raise RuntimeError("\n".join(error_list))

        self._config = configuration
        return self._config

    def _get_manifest_schema_file(self):

        return os.path.join(self._get_dataset_schema_dir(), 'manifest.schema.json')

    def _get_dataset_schema_dir(self):

        if not hasattr(self, '_dataset_schema_dir'):
            dir_path = os.path.dirname(os.path.realpath(__file__))
            self._dataset_schema_dir = os.path.join(dir_path, '../', '../', 'spec', 'datasets', 'djornl')

        return self._dataset_schema_dir

    def _get_manifest(self, configuration):
        """
        Read the manifest file, which contains path and file type info, and validate it.
        The manifest is expected to be at ROOT_DATA_PATH/manifest.yaml
        """

        schema_file = self._get_manifest_schema_file()

        # load the manifest and validate it against the schema
        manifest_file = os.path.join(configuration['ROOT_DATA_PATH'], 'manifest.yaml')

        try:
            with open(manifest_file) as fd:
                manifest = yaml.safe_load(fd)
        except FileNotFoundError:
            raise RuntimeError(
                f"No manifest file found at {manifest_file}.\n"
                "Please ensure that you have created a manifest that lists the files "
                "in the release"
            )

        try:
            validated_manifest = run_validator(
                schema_file=schema_file,
                data=manifest
            )
        except Exception as err:
            print(err)
            raise RuntimeError(
                "The manifest file failed validation. Please recheck the file and try again."
            )

        return validated_manifest

    def _get_file_reader(self, fd, file):
        '''Given a dict containing file information, instantiate the correct type of parser'''

        delimiter = '\t'
        if 'file_format' in file and file['file_format'].lower() == 'csv' or file['path'].lower().endswith('.csv'):
            delimiter = ','
        return csv.reader(fd, delimiter=delimiter)

    def parser_gen(self, file):
        """generator function to parse a file"""
        expected_col_count = 0
        with open(file['file_path'], newline='') as fd:
            csv_reader = self._get_file_reader(fd, file)
            line_no = 0
            for row in csv_reader:
                line_no += 1
                if not len(row) or row[0][0] == '#':
                    # comment / metadata
                    continue

                cols = [c.strip() for c in row]

                if len(cols) == expected_col_count:
                    yield (line_no, cols, None)
                    continue

                # if we didn't get the expected number of cols:
                if expected_col_count == 0:
                    # this is the header row; set up the expected column count
                    expected_col_count = len(cols)
                    yield (line_no, [c.lower() for c in cols], None)
                    continue

                # otherwise, this row does not have the correct number of columns
                col_count = len(cols)
                msg = f"expected {expected_col_count} cols, found {col_count}"
                yield(line_no, None, f"{file['path']} line {line_no}: {msg}")

    def check_headers(self, headers, validator=None):
        """
        Ensure that the file headers contain required columns for the data type. Checks the schema
        in the validator to ensure that all required fields are present in the headers.

        :param headers: (list)          list containing headers

        :param validator: (obj)         validator object, with the appropriate schema loaded

        :return missing_headers: (list) list of required headers that are missing from the input.
                                        If the list of headers supplied is valid--i.e. it
                                        contains all the fields marked as required in the validator
                                        schema--or no validator has been supplied, the method
                                        returns an empty list
        """

        if validator is None:
            return []

        # check that each required header in the schema is present in headers
        required_props = validator.schema['required']
        return [i for i in required_props if i not in headers]

    def remap_object(self, raw_data, remap_functions):
        """
        Given a dict, raw_data, create a new dict, remapped_data, using the functions in the
        dictionary `remap_functions`.

        :param raw_data: (dict)         input data for remapping

        :param remap_fn: (dict)         mapping of output param names to functions

                                        Each function should take the raw_data object as an
                                        argument and return the value for the output parameter.
                                        For parameters that can be copied over to the output
                                        object without modification, set the value to `None`
                                        instead of a function.

        :return remapped_data: (dict)   the remapped data!
        """
        remapped_data = {}
        for (key, function) in remap_functions.items():
            # these keys get copied over unchanged to the new object if they exist in the input obj
            if function is None:
                if key in raw_data:
                    remapped_data[key] = raw_data[key]
            else:
                remapped_data[key] = function(raw_data)

        return remapped_data

    def process_file(self, file, remap_fn, store_fn, err_list, validator=None):
        """ process an input file to generate a dataset and possibly an error list

        Each valid line in the file is turned into a dictionary using the header row, and then
        validated against the csv validation schema in spec/datasets/djornl/csv_<file_type>.
        If that completes successfully, it is transformed using the functions in the dictionary
        `remap_fn`, checked for uniqueness against existing data, and saved to a dictionary. Once
        all files of a certain type have been processed, results can be saved to Arango.

        Any errors that occur during parsing and processing are accumulated in `err_list`.

        :param file: (dict)             file data
        :param remap_fn: (dict)         mapping of output param names to functions
                                        each function should take the row data object as input and
                                        return the value for the output parameter

        :param store_fn: (func)         function to store the results of the remapping

        :param err_list: (list)         error list

        :param validator: (Validator)   jsonschema validator object

        """
        file_parser = self.parser_gen(file)
        try:
            (line_no, cols, err_str) = next(file_parser)
        except StopIteration:
            # no valid lines found in the file
            err_list.append(f"{file['path']}: no header line found")
            return

        missing_headers = self.check_headers(cols, validator)
        if missing_headers:
            err_list.append(
                f"{file['path']}: missing required headers: " + ", ".join(sorted(missing_headers))
            )
            return
        headers = cols
        n_stored = 0
        for (line_no, cols, err_str) in file_parser:
            # mismatch in number of cols
            if cols is None:
                err_list.append(err_str)
                continue

            # merge headers with cols to create an object
            row_object = dict(zip(headers, cols))

            if validator is not None:
                # validate the object
                if not validator.is_valid(row_object):
                    err_msg = "".join(
                        f"{file['path']} line {line_no}: " + e.message
                        for e in sorted(validator.iter_errors(row_object), key=str)
                    )
                    err_list.append(err_msg)
                    continue

            try:
                # transform it using the remap_functions
                datum = self.remap_object(row_object, remap_fn)
            except Exception as err:
                err_type = type(err)
                err_list.append(
                    f"{file['path']} line {line_no}: error remapping data: {err_type} {err}"
                )
                continue

            # and store it
            storage_error = store_fn(datum)
            if storage_error is None:
                n_stored += 1
            else:
                err_list.append(f"{file['path']} line {line_no}: " + storage_error)

        if not n_stored:
            err_list.append(f"{file['path']}: no valid data found")

    def load_edges(self):
        """Load edge data from the set of edge files"""

        # dict of nodes, indexed by node ID (node1 and node2 from the file)
        node_ix = {}
        # dict of edges, indexed by node1__node2__edge_type
        edge_ix = {}
        # error accumulator
        err_list = []

        schema_file = os.path.join(self._get_dataset_schema_dir(), 'csv_edge.yaml')
        validator = get_schema_validator(schema_file=schema_file)

        node_name = self.config('node_name')
        # these functions remap the values in the columns of the input file to
        # appropriate values to go into Arango
        # note that the functions that assume the presence of a certain key in the input
        # can do so because that key is in a 'required' property in the CSV spec file
        remap_functions = {
            # create a unique key for each record
            '_key': lambda row: '__'.join([row[_] for _ in ['node1', 'node2', 'edge_type', 'score']]),
            'node1': None,  # this will be deleted in the 'store' step
            'node2': None,  # as will this
            '_from': lambda row: node_name + '/' + row['node1'],
            '_to': lambda row: node_name + '/' + row['node2'],
            'score': lambda row: float(row['score']),
            'edge_type': None,
        }

        # store edge data, checking for potential duplicates
        def store_edges(datum):
            # there should only be one value for each node<->node edge of a given type,
            # so use these values as an index key
            edge_key = "__".join([*sorted([datum['node1'], datum['node2']]), datum['edge_type']])

            if edge_key in edge_ix:
                # duplicate lines can be ignored
                if datum['score'] == edge_ix[edge_key]['score']:
                    return None
                # report non-matching data
                return f"duplicate data for edge {edge_key}"

            # keep track of the nodes mentioned in this edge set
            for node_n in ["1", "2"]:
                node_ix[datum[f"node{node_n}"]] = {'_key': datum[f"node{node_n}"]}
                del datum[f"node{node_n}"]

            edge_ix[edge_key] = datum
            return None

        for file in self.config('edge_files'):
            self.process_file(
                file=file,
                remap_fn=remap_functions,
                store_fn=store_edges,
                err_list=err_list,
                validator=validator,
            )

        if len(err_list):
            raise RuntimeError('\n'.join(err_list))

        return {
            'nodes': node_ix.values(),
            'edges': edge_ix.values(),
        }

    def load_nodes(self):
        """Load node metadata"""

        node_ix = {}
        err_list = []

        schema_file = os.path.join(self._get_dataset_schema_dir(), 'csv_node.yaml')
        validator = get_schema_validator(schema_file=schema_file)

        def go_terms(row):
            if 'go_terms' in row and len(row['go_terms']):
                return [c.strip() for c in row['go_terms'].split(',')]
            return []

        remap_functions = {
            # these pass straight through
            'gene_full_name': None,
            'gene_model_type': None,
            'gene_symbol': None,
            'go_description': None,
            'mapman_bin': None,
            'mapman_description': None,
            'mapman_name': None,
            'node_type': None,
            'pheno_aragwas_id': None,
            'pheno_description': None,
            'pheno_pto_description': None,
            'pheno_pto_name': None,
            'pheno_ref': None,
            'tair_computational_description': None,
            'tair_curator_summary': None,
            'tair_short_description': None,
            'transcript': None,
            'user_notes': None,
            # rename
            '_key': lambda row: row['node_id'],
            # see functions above
            'go_terms': go_terms,
        }

        # store nodes in a dict indexed by _key
        def store_nodes(datum):
            # check whether we have this node already
            if datum['_key'] in node_ix:
                # report non-matching data
                if datum != node_ix[datum['_key']]:
                    return f"duplicate data for node {datum['_key']}"
                # otherwise, it's duplicated line: ignore
                return None

            node_ix[datum['_key']] = datum
            return None

        for file in self.config('node_files'):
            self.process_file(
                file=file,
                remap_fn=remap_functions,
                store_fn=store_nodes,
                err_list=err_list,
                validator=validator,
            )

        if len(err_list):
            raise RuntimeError('\n'.join(err_list))
        return {'nodes': node_ix.values()}

    def load_clusters(self):
        """Annotate genes with cluster ID fields."""

        # index of nodes
        node_ix = {}
        err_list = []

        schema_file = os.path.join(self._get_dataset_schema_dir(), 'csv_cluster.yaml')
        validator = get_schema_validator(schema_file=schema_file)

        # these functions remap the values in the columns of the input file to
        # appropriate values to go into Arango
        # the 'cluster_id' remap function is assigned below on a per-file basis
        remap_functions = {
            'node_ids': lambda row: [n.strip() for n in row['node_ids'].split(',')]
        }

        # store cluster IDs in a list under the key 'clusters'
        def store_clusters(datum):
            cluster_id = datum['cluster_id']
            for node_id in datum['node_ids']:
                if node_id not in node_ix:
                    node_ix[node_id] = {'_key': node_id, 'clusters': [cluster_id]}
                elif 'clusters' not in node_ix[node_id]:
                    node_ix[node_id]['clusters'] = [cluster_id]
                elif cluster_id not in node_ix[node_id]['clusters']:
                    node_ix[node_id]['clusters'].append(cluster_id)
            return None

        for file in self.config('cluster_files'):
            prefix = file['cluster_prefix']
            remap_functions['cluster_id'] = lambda row: prefix + ':' + row['cluster_id'].replace('Cluster', '')

            self.process_file(
                file=file,
                remap_fn=remap_functions,
                store_fn=store_clusters,
                err_list=err_list,
                validator=validator,
            )

        if len(err_list):
            raise RuntimeError('\n'.join(err_list))

        return {'nodes': list(node_ix.values())}

    def save_dataset(self, dataset):

        if 'nodes' in dataset and len(dataset['nodes']) > 0:
            self.save_docs(self.config('node_name'), dataset['nodes'])

        if 'edges' in dataset and len(dataset['edges']) > 0:
            self.save_docs(self.config('edge_name'), dataset['edges'])

    def save_docs(self, coll_name, docs, on_dupe='update'):

        resp = requests.put(
            self.config('API_URL') + '/api/v1/documents',
            params={'collection': coll_name, 'on_duplicate': on_dupe},
            headers={'Authorization': self.config('AUTH_TOKEN')},
            data='\n'.join(json.dumps(d) for d in docs)
        )
        if not resp.ok:
            raise RuntimeError(resp.text)

        print(f"Saved docs to collection {coll_name}!")
        print(resp.text)
        print('=' * 80)
        return resp

    def load_data(self):
        self.save_dataset(self.load_edges())
        self.save_dataset(self.load_nodes())
        self.save_dataset(self.load_clusters())
        return True

    def check_data_delta(self):
        edge_data = self.load_edges()
        node_data = self.load_nodes()
        clusters = self.load_clusters()

        self.check_deltas(edge_data=edge_data, node_data=node_data, cluster_data=clusters)

    def check_deltas(self, edge_data={}, node_data={}, cluster_data={}):

        edges_nodelist = set([e['_key'] for e in edge_data['nodes']])
        nodes_nodelist = set([e['_key'] for e in node_data['nodes']])
        clusters_nodelist = set([e['_key'] for e in cluster_data['nodes']])
        all_nodes = edges_nodelist.union(nodes_nodelist).union(clusters_nodelist)

        # check all nodes in cluster_data have node data
        cluster_no_node_set = clusters_nodelist.difference(nodes_nodelist)
        if cluster_no_node_set:
            print({'clusters with no node metadata': cluster_no_node_set})

        # check all nodes in the edge_data have node data
        edge_no_node_set = edges_nodelist.difference(nodes_nodelist)
        if edge_no_node_set:
            print({'edges with no node metadata': edge_no_node_set})

        # check all nodes are in the edge_data set
        node_no_edge_set = nodes_nodelist.difference(edges_nodelist)
        if node_no_edge_set:
            print({'nodes not in an edge': node_no_edge_set})

        # count all edges
        print("Dataset contains " + str(len(edge_data['edges'])) + " edges")
        # count all nodes
        print("Dataset contains " + str(len(all_nodes)) + " nodes")


if __name__ == '__main__':
    parser = DJORNL_Parser()
    try:
        parser.load_data()
    except Exception as err:
        print(err)
        exit(1)
