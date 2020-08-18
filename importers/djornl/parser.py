"""
Loads the Dan Jacobson/ORNL group's gene and phenotype network data into
arangodb.

Running this requires a set of source files provided by the ORNL group.
"""
import json
import requests
import os
import csv

import importers.utils.config as config


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
        configuration['_NODE_NAME'] = 'djornl_node'
        configuration['_EDGE_NAME'] = 'djornl_edge'

        # Path config
        configuration['_NODE_PATH'] = os.path.join(
            configuration['ROOT_DATA_PATH'],
            'aranet2-aragwas-MERGED-AMW-v2_091319_nodeTable.csv'
        )
        configuration['_NODE_FILE_COL_COUNT'] = 20

        configuration['_EDGE_PATH'] = os.path.join(
            configuration['ROOT_DATA_PATH'],
            'merged_edges-AMW-060820_AF.tsv'
        )
        configuration['_EDGE_FILE_COL_COUNT'] = 5

        _CLUSTER_BASE = os.path.join(configuration['ROOT_DATA_PATH'], 'cluster_data')
        configuration['_CLUSTER_PATHS'] = {
            'markov_i2': os.path.join(
                _CLUSTER_BASE,
                'out.aranetv2_subnet_AT-CX_top10percent_anno_AF_082919.abc.I2_named.tsv'
            ),
            'markov_i4': os.path.join(
                _CLUSTER_BASE,
                'out.aranetv2_subnet_AT-CX_top10percent_anno_AF_082919.abc.I4_named.tsv'
            ),
            'markov_i6': os.path.join(
                _CLUSTER_BASE,
                'out.aranetv2_subnet_AT-CX_top10percent_anno_AF_082919.abc.I6_named.tsv'
            ),
        }
        self._config = configuration
        return self._config

    def load_edges(self):
        # Headers and sample row:
        # node1	node2	edge	edge_descrip	layer_descrip
        # AT1G01370	AT1G57820	4.40001558779779	AraNetv2_log-likelihood-score	AraNetv2-LC_lit-curated-ppi
        edge_remap = {
            'AraGWAS-Phenotype_Associations': 'pheno_assn',
            'AraNetv2-CX_pairwise-gene-coexpression': 'gene_coexpr',
            'AraNetv2-DC_domain-co-occurrence': 'domain_co_occur',
            'AraNetv2-HT_high-throughput-ppi': 'ppi_hithru',
            'AraNetv2-LC_lit-curated-ppi': 'ppi_liter',
        }

        # dict of nodes, indexed by node ID (node1 and node2 from the file)
        node_ix = {}
        edges = []
        node_name = self.config('_NODE_NAME')
        expected_col_count = self.config('_EDGE_FILE_COL_COUNT')

        with open(self.config('_EDGE_PATH')) as fd:
            csv_reader = csv.reader(fd, delimiter='\t')
            next(csv_reader, None)  # skip headers
            line_no = 1
            for row in csv_reader:
                line_no += 1

                cols = [c.strip() for c in row]
                if len(cols) != expected_col_count:
                    n_cols = len(cols)
                    raise RuntimeError(f"line {line_no}: expected {expected_col_count} cols, found {n_cols}")

                node_ix[cols[0]] = 1
                node_ix[cols[1]] = 1
                edge_type = cols[4]
                if edge_type not in edge_remap:
                    raise RuntimeError(f"line {line_no}: invalid edge type: {edge_type}")

                edges.append({
                    '_key': f'{cols[0]}__{cols[1]}__{edge_remap[edge_type]}__{cols[2]}',
                    '_from': f'{node_name}/{cols[0]}',
                    '_to': f'{node_name}/{cols[1]}',
                    'score': float(cols[2]),
                    'edge_type': edge_remap[edge_type],
                })

        return {
            'nodes': [{'_key': n} for n in node_ix.keys()],
            'edges': edges,
        }

    def load_node_metadata(self):
        """Load node metadata"""

        nodes = []
        valid_node_types = ['gene', 'pheno']
        expected_col_count = self.config('_NODE_FILE_COL_COUNT')
        with open(self.config('_NODE_PATH')) as fd:
            csv_reader = csv.reader(fd, delimiter=',')
            next(csv_reader, None)  # skip headers
            line_no = 1
            for row in csv_reader:
                line_no += 1

                cols = [c.strip() for c in row]
                if len(cols) != expected_col_count:
                    n_cols = len(cols)
                    raise RuntimeError(f"line {line_no}: expected {expected_col_count} cols, found {n_cols}")

                _key = cols[0]
                node_type = cols[1]
                if node_type not in valid_node_types:
                    raise RuntimeError(f"line {line_no}: invalid node type: {node_type}")

                go_terms = [c.strip() for c in cols[10].split(',')] if len(cols[10]) else []

                doc = {
                    '_key': _key,
                    'node_type': node_type,
                    'transcript': cols[2],
                    'gene_symbol': cols[3],
                    'gene_full_name': cols[4],
                    'gene_model_type': cols[5],
                    'tair_computational_desc': cols[6],
                    'tair_curator_summary': cols[7],
                    'tair_short_desc': cols[8],
                    'go_descr': cols[9],
                    'go_terms': go_terms,
                    'mapman_bin': cols[11],
                    'mapman_name': cols[12],
                    'mapman_desc': cols[13],
                    'pheno_aragwas_id': cols[14],
                    'pheno_desc1': cols[15],
                    'pheno_desc2': cols[16],
                    'pheno_desc3': cols[17],
                    'pheno_ref': cols[18],
                    'user_notes': cols[19],
                }
                nodes.append(doc)

        return {'nodes': nodes}

    def load_cluster_data(self):
        """Annotate genes with cluster ID fields."""

        # index of nodes
        node_ix = {}

        cluster_paths = self.config('_CLUSTER_PATHS')
        for (cluster_label, path) in cluster_paths.items():
            with open(path) as fd:
                csv_reader = csv.reader(fd, delimiter='\t')
                for row in csv_reader:
                    if len(row) > 1:
                        # remove the 'Cluster' text and replace it with cluster_label
                        cluster_id = cluster_label + ':' + row[0].replace('Cluster', '')

                        node_keys = row[1:]
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
            self.save_docs(self.config('_NODE_NAME'), dataset['nodes'])

        if 'edges' in dataset and len(dataset['edges']) > 0:
            self.save_docs(self.config('_EDGE_NAME'), dataset['edges'])

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
