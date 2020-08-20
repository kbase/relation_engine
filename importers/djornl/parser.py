"""
Loads the Dan Jacobson/ORNL group's gene and phenotype network data into
arangodb.

Running this requires a set of source files provided by the ORNL group.
"""
import json
import requests
import os
import csv
import yaml

import importers.utils.config as config
from relation_engine_server.utils.json_validation import run_validator


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

        return os.path.join('/app', 'spec', 'datasets', 'djornl', 'manifest.schema.json')

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
                + "Please ensure that you have created a manifest that lists the files "
                + "in the release"
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
        with open(file['file_path']) as fd:
            csv_reader = self._get_file_reader(fd, file)
            line_no = 0
            for row in csv_reader:
                line_no += 1
                if len(row) <= 1 or row[0][0] == '#':
                    # comment / metadata
                    continue

                cols = [c.strip() for c in row]

                if len(cols) == expected_col_count:
                    yield (line_no, cols)
                    continue

                # if we didn't get the expected number of cols:
                if expected_col_count == 0:
                    # this is the header row; set up the expected column count
                    expected_col_count = len(cols)
                    yield (line_no, [c.lower() for c in cols])
                    continue

                # otherwise, this row does not have the correct number of columns
                n_cols = len(cols)
                raise RuntimeError(
                    f"{file['path']} line {line_no}: "
                    + f"expected {expected_col_count} cols, found {n_cols}"
                )

    def load_edges(self):
        # Headers and sample row:
        # node1	node2	edge	edge_descrip	layer_descrip
        # AT1G01370	AT1G57820	4.40001558779779	AraNetv2_log-likelihood-score	AraNetv2-LC_lit-curated-ppi
        edge_type_remap = {
            'AraGWAS-Phenotype_Associations': 'pheno_assn',
            'AraNetv2-CX_pairwise-gene-coexpression': 'gene_coexpr',
            'AraNetv2-DC_domain-co-occurrence': 'domain_co_occur',
            'AraNetv2-HT_high-throughput-ppi': 'ppi_hithru',
            'AraNetv2-LC_lit-curated-ppi': 'ppi_liter',
        }

        # dict of nodes, indexed by node ID (node1 and node2 from the file)
        node_ix = {}
        edges = []
        node_name = self.config('node_name')

        def edge_type(row):
            if row['layer_descrip'] not in edge_type_remap:
                raise RuntimeError(
                    f"{file['path']} line {line_no}: invalid edge type: {row['layer_descrip']}"
                )
            return edge_type_remap[row['layer_descrip']]

        def _key(row):
            return '__'.join([
                row['node1'],
                row['node2'],
                edge_type(row),
                row['edge'],
            ])

        # these functions remap the values in the columns of the input file to
        # appropriate values to go into Arango
        remap_functions = {
            '_from': lambda row: node_name + '/' + row['node1'],
            '_to': lambda row: node_name + '/' + row['node2'],
            'score': lambda row: float(row['edge']),
            'edge_type': edge_type,
            '_key': _key,
        }

        for file in self.config('edge_files'):
            file_parser = self.parser_gen(file)
            headers = []

            while True:
                try:
                    (line_no, cols) = next(file_parser)
                except StopIteration:
                    break

                if len(headers) == 0:
                    headers = cols
                    continue

                # merge headers with cols to create an object
                row_object = dict(zip(headers, cols))
                # transform it using the remap_functions
                datum = {key: func(row_object) for (key, func) in remap_functions.items()}
                edges.append(datum)

                # keep track of the nodes mentioned in this edge set
                for node in ["1", "2"]:
                    node_ix[row_object[f"node{node}"]] = 1

        return {
            'nodes': [{'_key': n} for n in node_ix.keys()],
            'edges': edges,
        }

    def load_node_metadata(self):
        """Load node metadata"""

        nodes = []
        valid_node_types = ['gene', 'pheno']

        def go_terms(row):
            if len(row['go_terms']):
                return [c.strip() for c in row_object['go_terms'].split(',')]
            return []

        def node_type(row):
            if row['node_type'] not in valid_node_types:
                raise RuntimeError(
                    f"{file['path']} line {line_no}: invalid node type: {row['node_type']}"
                )
            return row['node_type']

        remap_functions = {
            # these pass straight through
            'transcript': None,
            'gene_symbol': None,
            'gene_full_name': None,
            'gene_model_type': None,
            'tair_computational_description': None,
            'tair_short_description': None,
            'tair_curator_summary': None,
            'mapman_bin': None,
            'mapman_name': None,
            'pheno_aragwas_id': None,
            'pheno_ref': None,
            'user_notes': None,
            # rename
            '_key': lambda row: row['node_id'],
            'go_description': lambda row: row['go_descr'],
            'mapman_description': lambda row: row['mapman_descr'],
            'pheno_description': lambda row: row['pheno_descrip1'],
            'pheno_pto_name': lambda row: row['pheno_descrip2'],
            'pheno_pto_description': lambda row: row['pheno_descrip3'],
            # see functions above
            'node_type': node_type,
            'go_terms': go_terms,
        }

        for file in self.config('node_files'):
            file_parser = self.parser_gen(file)
            headers = []

            while True:
                try:
                    (line_no, cols) = next(file_parser)
                except StopIteration:
                    break

                if len(headers) == 0:
                    headers = cols
                    continue

                # merge with headers to form an object, then remap to create Arango-ready data
                row_object = dict(zip(headers, cols))

                datum = {}
                for (key, func) in remap_functions.items():
                    if func is None:
                        datum[key] = row_object[key]
                    else:
                        datum[key] = func(row_object)
                nodes.append(datum)

        return {'nodes': nodes}

    def load_cluster_data(self):
        """Annotate genes with cluster ID fields."""

        # index of nodes
        node_ix = {}
        for file in self.config('cluster_files'):
            cluster_label = file['cluster_prefix']
            headers = []
            file_parser = self.parser_gen(file)

            while True:
                try:
                    (line_no, cols) = next(file_parser)
                except StopIteration:
                    break

                if len(headers) == 0:
                    headers = cols
                    continue

                # remove the 'Cluster' text and replace it with cluster_label
                cluster_id = cluster_label + ':' + cols[0].replace('Cluster', '')
                node_keys = [n.strip() for n in cols[1].split(',')]
                for key in node_keys:
                    if key not in node_ix:
                        node_ix[key] = [cluster_id]
                    elif cluster_id not in node_ix[key]:
                        node_ix[key].append(cluster_id)

        # gather a list of cluster IDs for each node
        nodes = [{
            '_key': key,
            'clusters': cluster_data
        } for (key, cluster_data) in node_ix.items()]

        return {'nodes': nodes}

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
        self.save_dataset(self.load_node_metadata())
        self.save_dataset(self.load_cluster_data())

    def check_data_delta(self):
        edge_data = self.load_edges()
        node_metadata = self.load_node_metadata()
        clusters = self.load_cluster_data()

        self.check_deltas(edge_data=edge_data, node_metadata=node_metadata, cluster_data=clusters)

    def check_deltas(self, edge_data={}, node_metadata={}, cluster_data={}):

        edge_nodes = set([e['_key'] for e in edge_data['nodes']])
        node_metadata_nodes = set([e['_key'] for e in node_metadata['nodes']])
        cluster_nodes = set([e['_key'] for e in cluster_data['nodes']])
        all_nodes = edge_nodes.union(node_metadata_nodes).union(cluster_nodes)

        # check all nodes in cluster_data have node_metadata
        clstr_no_node_md_set = cluster_nodes.difference(node_metadata_nodes)
        if clstr_no_node_md_set:
            print({'clusters with no node metadata': clstr_no_node_md_set})

        # check all nodes in the edge_data have node_metadata
        edge_no_node_md_set = edge_nodes.difference(node_metadata_nodes)
        if edge_no_node_md_set:
            print({'edges with no node metadata': edge_no_node_md_set})

        # count all edges
        print("Dataset contains " + str(len(edge_data['edges'])) + " edges")
        # count all nodes
        print("Dataset contains " + str(len(all_nodes)) + " nodes")
