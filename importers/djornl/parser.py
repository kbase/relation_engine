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
import argparse
import csv
import json
import logging
import os
import requests
import yaml

import importers.utils.config as config
from relation_engine_server.utils.json_validation import run_validator, get_schema_validator

LOGGER = logging.getLogger(__name__)


class DJORNL_Parser(object):

    def __init__(self):

        # dict of nodes, indexed by node ID (node1 and node2 from the file)
        self.node_ix = {}
        # dict of edges, indexed by node1__node2__edge_type
        self.edge_ix = {}

        # the order in which to parse the different data files
        self.parse_order = ['edges', 'nodes', 'clusters']

    def config(self, value):
        if not hasattr(self, '_config'):
            self._configure()

        if value not in self._config:
            raise KeyError(f'No such config value: {value}')

        return self._config[value]

    def _configure(self):

        configuration = config.load_from_env(
            extra_required=['ROOT_DATA_PATH']
        )

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
            self._dataset_schema_dir = os.path.join(
                dir_path, '../', '../', 'spec', 'datasets', 'djornl'
            )

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
        if file.get('file_format', '').lower() == 'csv' or file['path'].lower().endswith('.csv'):
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

        :return header_errs: (dict)     dict of header errors:
                                        'missing': required headers that are missing from the input
                                        'invalid': headers that should not be in the input
                                        'duplicate': duplicated headers (data would be overwritten)
                                        If the list of headers supplied is valid--i.e. it
                                        contains all the fields marked as required in the validator
                                        schema--or no validator has been supplied, the method
                                        returns an empty dict
        """

        if validator is None:
            return {}

        header_errs = {}

        all_headers = {}
        # ensure we don't have any duplicate headers
        for h in headers:
            if h in all_headers:
                all_headers[h] += 1
            else:
                all_headers[h] = 1

        duplicate_headers = [h for h in all_headers.keys() if all_headers[h] != 1]
        if duplicate_headers:
            header_errs['duplicate'] = duplicate_headers

        # check that each required header in the schema is present in headers
        required_props = validator.schema['required']
        missing_headers = [i for i in required_props if i not in headers]
        if missing_headers:
            header_errs['missing'] = missing_headers

        if not validator.schema.get('additionalProperties', True):
            all_props = validator.schema['properties'].keys()
            extra_headers = [i for i in headers if i not in all_props]
            if extra_headers:
                header_errs['invalid'] = extra_headers

        return header_errs

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
        LOGGER.info("Parsing " + file['data_type'] + " file " + file['file_path'])
        file_parser = self.parser_gen(file)

        def add_error(error):
            LOGGER.error(error)
            err_list.append(error)

        try:
            (line_no, cols, err_str) = next(file_parser)
        except StopIteration:
            # no valid lines found in the file
            add_error(f"{file['path']}: no header line found")
            return

        header_errors = self.check_headers(cols, validator)
        if header_errors.keys():
            err_str = {
                'duplicate': 'duplicate',
                'missing': 'missing required',
                'invalid': 'invalid additional',
            }
            for err_type in ['missing', 'invalid', 'duplicate']:
                if err_type in header_errors:
                    add_error(
                        f"{file['path']}: {err_str[err_type]} headers: "
                        + ", ".join(sorted(header_errors[err_type]))
                    )
            return

        headers = cols
        n_stored = 0
        for (line_no, cols, err_str) in file_parser:
            # mismatch in number of cols
            if cols is None:
                add_error(err_str)
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
                    add_error(err_msg)
                    continue

            try:
                # transform it using the remap_functions
                datum = self.remap_object(row_object, remap_fn)
            except Exception as err:
                err_type = type(err)
                add_error(
                    f"{file['path']} line {line_no}: error remapping data: {err_type} {err}"
                )
                continue

            # and store it
            storage_error = store_fn(datum)
            if storage_error is None:
                n_stored += 1
            else:
                add_error(f"{file['path']} line {line_no}: " + storage_error)

        if not n_stored:
            add_error(f"{file['path']}: no valid data found")

    def store_parsed_edge_data(self, datum):
        """
        store node and edge data in the node (node_ix) and edge (edge_ix) indexes respectively
        Nodes are indexed by the '_key' attribute.
        Parsed edge data only contains node '_key' values.

        Edges are indexed by the unique combination of the two node IDs and the edge type. It is
        assumed that if there is more than one score for a given combination of node IDs and edge
        type, the datum is erroneous.
        """

        # there should only be one value for each node<->node edge of a given type,
        # so use these values as an index key
        # sort the nodes to ensure no dupes slip through
        edge_key = "__".join([*sorted([datum['node1'], datum['node2']]), datum['edge_type']])

        if edge_key in self.edge_ix:
            # duplicate lines can be ignored
            if datum['score'] == self.edge_ix[edge_key]['score']:
                return None
            # report non-matching data
            return f"duplicate data for edge {edge_key}"

        # keep track of the nodes mentioned in this edge set
        for node_n in ["1", "2"]:
            _key = datum[f"node{node_n}"]
            if _key not in self.node_ix:
                self.node_ix[_key] = {"_key": _key}
            del datum[f"node{node_n}"]

        self.edge_ix[edge_key] = datum
        return None

    def load_edges(self):
        """Load edge data from the set of edge files"""

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
            '_key': lambda row: '__'.join(
                [row[_] for _ in ['node1', 'node2', 'edge_type', 'score']]
            ),
            'node1': None,  # this will be deleted in the 'store' step
            'node2': None,  # as will this
            '_from': lambda row: node_name + '/' + row['node1'],
            '_to': lambda row: node_name + '/' + row['node2'],
            'score': lambda row: float(row['score']),
            'edge_type': None,
        }

        for file in self.config('edge_files'):
            self.process_file(
                file=file,
                remap_fn=remap_functions,
                store_fn=self.store_parsed_edge_data,
                err_list=err_list,
                validator=validator,
            )

        return {
            'nodes': list(self.node_ix.values()),
            'edges': list(self.edge_ix.values()),
            'err_list': err_list,
        }

    def _try_node_merge(self, existing_node, new_node, path=[]):
        """
        Try to merge two data structures. These should be JSON compatible, so they will be limited
        to lists, dicts, and scalar data types.

        This method tests the keys/values of the two dict objects provided and depending on the type
        of the values, merges them or records an error:

        - scalar (strings, ints, floats, etc.): record an error on mismatches
        - list: merge list contents, removing duplicates and preserving order
        - dict: run _try_node_merge recursively on it
        - mismatch of data types between the two nodes: record an error

        :param existing_node: (dict)    existing node
        :param new_node: (dict)         node data to be merged into it
        :param path: (list)             path to this node in a larger data structure

        :return (merge, err_list): (tuple)
                                        If successful, the method returns the merged dict and []
                                        If there were errors, err_list will be populated with the
                                        keys/values where mismatches occurred.
        """

        # merge the dictionaries
        merge = {**existing_node, **new_node}

        # find the shared keys -- keys in both existing and new nodes where the values differ
        shared_keys = [
            i for i in new_node
            if i in existing_node and new_node[i] != existing_node[i]
        ]

        # if there were no shared keys, return the merged list
        if not shared_keys:
            return (merge, [])

        # otherwise, we need to remove the shared keys and examine them individually
        for k in shared_keys:
            del merge[k]

        err_list = []
        # go through the dict keys, checking their type
        for k in sorted(shared_keys):
            value_type = type(existing_node[k])

            # do the types match? If not, these values cannot be merged
            if type(new_node[k]) != value_type:
                err_list.append("/".join(path+[k]))
                continue

            if value_type == list:
                # merge lists, preserving order. Data type agnostic.
                merge[k] = []
                for i in existing_node[k] + new_node[k]:
                    if i not in merge[k]:
                        merge[k].append(i)
                continue

            elif value_type == dict:
                # recursively check dict data using _try_node_merge
                (k_merged, k_errs) = self._try_node_merge(existing_node[k], new_node[k], path+[k])
                if k_errs:
                    err_list = err_list + k_errs
                    continue
                merge[k] = k_merged

            else:
                # this is a scalar (string, number, etc.) so it can't be merged
                err_list.append("/".join(path+[k]))

        # at some point, it may be useful to examine these errors in more detail
        if err_list:
            merge = None
        return (merge, err_list)

    def store_parsed_node_data(self, datum):
        """
        store node data in the node index, node_ix, indexed by the node _key

        If a node is already present, new data is checked for conflicts with existing data
        """
        # check whether we have this node already
        if datum['_key'] in self.node_ix:
            # identical data: ignore it
            if datum == self.node_ix[datum['_key']]:
                return None

            # try merging the data
            (merged, err_list) = self._try_node_merge(self.node_ix[datum['_key']], datum)
            if err_list:
                return "duplicate data for node " + datum['_key']
            datum = merged

        self.node_ix[datum['_key']] = datum
        return None

    def load_nodes(self):
        """Load node metadata"""

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
            'pheno_reference': None,
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

        for file in self.config('node_files'):
            self.process_file(
                file=file,
                remap_fn=remap_functions,
                store_fn=self.store_parsed_node_data,
                err_list=err_list,
                validator=validator,
            )

        return {
            'nodes': self.node_ix.values(),
            'err_list': err_list,
        }

    def store_parsed_cluster_data(self, datum):
        """
        store remapped cluster data

        The input is in the form

        {'cluster_id': cluster_id, 'node_ids': [node_id_1, node_id_2, node_id_3, ...]}

        Cluster IDs are stored in the 'clusters' node attribute as a list, with new IDs added to
        (rather than replacing) existing IDs
        """
        cluster_id = datum['cluster_id']
        # gather a list of cluster IDs for each node
        for node_id in datum['node_ids']:
            if node_id not in self.node_ix:
                self.node_ix[node_id] = {'_key': node_id, 'clusters': [cluster_id]}
            elif 'clusters' not in self.node_ix[node_id]:
                self.node_ix[node_id]['clusters'] = [cluster_id]
            elif cluster_id not in self.node_ix[node_id]['clusters']:
                self.node_ix[node_id]['clusters'].append(cluster_id)
        return None

    def load_clusters(self):
        """Annotate genes with cluster ID fields."""

        err_list = []

        schema_file = os.path.join(self._get_dataset_schema_dir(), 'csv_cluster.yaml')
        validator = get_schema_validator(schema_file=schema_file)

        # these functions remap the values in the columns of the input file to
        # appropriate values to go into Arango
        # the 'cluster_id' remap function is assigned below on a per-file basis
        remap_functions = {
            'node_ids': lambda row: [n.strip() for n in row['node_ids'].split(',')]
        }

        for file in self.config('cluster_files'):
            prefix = file['cluster_prefix']
            remap_functions['cluster_id'] = (
                lambda row: prefix + ':' + row['cluster_id'].replace('Cluster', '')
            )

            self.process_file(
                file=file,
                remap_fn=remap_functions,
                store_fn=self.store_parsed_cluster_data,
                err_list=err_list,
                validator=validator,
            )

        return {
            'nodes': list(self.node_ix.values()),
            'err_list': err_list,
        }

    def save_dataset(self, dataset=None):

        if dataset is None:
            dataset = {
                'nodes': list(self.node_ix.values()),
                'edges': list(self.edge_ix.values()),
            }

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

    def load_data(self, dry_run=False):
        all_errs = []
        method_ix = {
            'clusters': self.load_clusters,
            'edges': self.load_edges,
            'nodes': self.load_nodes,
        }
        for data_type in self.parse_order:
            output = method_ix[data_type]()
            if output['err_list']:
                all_errs = all_errs + output['err_list']

        # save the dataset, unless this is a dry run
        if not dry_run:
            self.save_dataset()

        # report stats on the data that has been gathered
        return self.summarise_dataset(all_errs)

    def summarise_dataset(self, errs):
        """summarise the data that has been loaded"""

        # go through the node index, checking for nodes that only have one attribute ('_key') or
        # were loaded from the clusters files, with only '_key' and 'clusters' attributes

        node_type_ix = {
            '__NO_TYPE__': 0
        }
        node_data = {
            'key_only': [],
            'cluster': [],
            'full': []
        }

        for node in self.node_ix.values():
            if len(node.keys()) == 2 and 'clusters' in node:
                node_data['cluster'].append(node)
            elif len(node.keys()) == 1:
                node_data['key_only'].append(node)
            else:
                node_data['full'].append(node)

            if 'node_type' in node:
                if node['node_type'] in node_type_ix:
                    node_type_ix[node['node_type']] += 1
                else:
                    node_type_ix[node['node_type']] = 1
            else:
                node_type_ix['__NO_TYPE__'] += 1

        nodes_in_edge_ix = {}
        edge_type_ix = {}
        for edge in self.edge_ix.values():
            nodes_in_edge_ix[edge['_from']] = 1
            nodes_in_edge_ix[edge['_to']] = 1
            if edge['edge_type'] in edge_type_ix:
                edge_type_ix[edge['edge_type']] += 1
            else:
                edge_type_ix[edge['edge_type']] = 1

        return {
            'nodes_total': len(self.node_ix.keys()),
            'edges_total': len(self.edge_ix.keys()),
            'nodes_in_edge': len(nodes_in_edge_ix.keys()),
            'node_type_count': node_type_ix,
            'edge_type_count': edge_type_ix,
            'node_data_available': {
                'key_only': len(node_data['key_only']),
                'cluster': len(node_data['cluster']),
                'full': len(node_data['full'])
            },
            'errors_total': len(errs),
            'errors': errs
        }


def format_summary(summary, output):
    if output == 'json':
        return json.dumps(summary)
    node_type_counts = [count for count in summary['node_type_count'].values()]
    edge_type_counts = [count for count in summary['node_type_count'].values()]
    values = [
        summary['nodes_total'],
        summary['edges_total'],
        summary['nodes_in_edge'],
        summary['node_data_available']['key_only'],
        summary['node_data_available']['cluster'],
        summary['node_data_available']['full'],
        summary.get('errors_total'),
    ] + node_type_counts + edge_type_counts
    value_width = max([len(str(value)) for value in values])
    node_type_names = dict(__NO_TYPE__="No type")
    node_types = "\n".join([(
            f"{count:{value_width}} {node_type_names.get(ntype, ntype)}"
            .format(value_width)
        )
        for ntype, count in summary['node_type_count'].items()
    ])
    edge_type_names = dict()
    edge_types = "\n".join([(
            f"{count:{value_width}} {edge_type_names.get(etype, etype)}"
            .format(value_width)
        )
        for etype, count in summary['edge_type_count'].items()
    ])
    text_summary = f"""
{summary['nodes_total']:{value_width}} Total nodes
{summary['edges_total']:{value_width}} Total edges
{summary['nodes_in_edge']:{value_width}} Nodes in edge
---
Node Types
{node_types:{value_width}}
---
Edge Types
{edge_types:{value_width}}
---
Node data available
{summary['node_data_available']['key_only']:{value_width}} Key only
{summary['node_data_available']['cluster']:{value_width}} Cluster
{summary['node_data_available']['full']:{value_width}} Full
---
{summary.get('errors_total'):{value_width}} Errors
""".format(value_width)
    return text_summary


def main():
    argparser = argparse.ArgumentParser(description='Load DJORNL data')
    argparser.add_argument(
        '--debug', action='store_true',
        help='Print errors in summary, by default only their count is printed.'
    )
    argparser.add_argument(
        '--dry-run', dest='dry', action='store_true',
        help='Perform all actions of the parser, except loading the data.'
    )
    argparser.add_argument(
        '--output', default='text',
        help='Specify the format of any output generated. (text or json)'
    )
    args = argparser.parse_args()
    parser = DJORNL_Parser()
    summary = dict()
    debug = args.debug
    try:
        summary = parser.load_data(dry_run=args.dry)
    except Exception as err:
        print('Unhandled exception', err)
        exit(1)
    errors = summary.get('errors')
    if summary:
        print(format_summary(summary, args.output))
    if errors:
        punctuation = ':' if debug else '.'
        error_output = f'Aborted with {len(errors)} errors{punctuation}\n'
        if debug:
            error_output += '\n'.join(errors)
        raise RuntimeError(error_output)


if __name__ == '__main__':
    main()
