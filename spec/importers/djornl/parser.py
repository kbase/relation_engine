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

    def config(self):
        if not hasattr(self, '_config'):
            return self._configure()

        return self._config

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
            'cluster_I2': os.path.join(
                _CLUSTER_BASE,
                'out.aranetv2_subnet_AT-CX_top10percent_anno_AF_082919.abc.I2_named.tsv'
            ),
            'cluster_I4': os.path.join(
                _CLUSTER_BASE,
                'out.aranetv2_subnet_AT-CX_top10percent_anno_AF_082919.abc.I4_named.tsv'
            ),
            'cluster_I6': os.path.join(
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
          'AraGWAS-Phenotype_Associations':         'pheno_assn',
          'AraNetv2-CX_pairwise-gene-coexpression': 'gene_coexpr',
          'AraNetv2-DC_domain-co-occurrence':       'domain_co_occur',
          'AraNetv2-HT_high-throughput-ppi':        'ppi_hithru',
          'AraNetv2-LC_lit-curated-ppi':            'ppi_liter',
        }

        node_ix = {}
        edges = []
        node_name = self.config()['_NODE_NAME']
        expected_col_count = self.config()['_EDGE_FILE_COL_COUNT']

        with open(self.config()['_EDGE_PATH']) as fd:
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
                if not edge_type in edge_remap:
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
        expected_col_count = self.config()['_NODE_FILE_COL_COUNT']
        with open(self.config()['_NODE_PATH']) as fd:
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
                if node_type != 'gene' and node_type != 'pheno':
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
        nodes = []
        cluster_paths = self.config()['_CLUSTER_PATHS']
        for (cluster_label, path) in cluster_paths.items():
            with open(path) as fd:
                csv_reader = csv.reader(fd, delimiter='\t')
                for row in csv_reader:
                    if len(row) > 1:
                        # remove the 'Cluster' text
                        cluster_id = row[0].replace('Cluster','')
                        gene_keys = row[1:]
                        nodes += [
                            {'_key': key, cluster_label: int(cluster_id)}
                            for key in gene_keys
                        ]

        return {'nodes': nodes}


    def save_dataset(self, dataset):

        if 'nodes' in dataset and len(dataset['nodes']) > 0:
            self.save_docs(self.config()['_NODE_NAME'], dataset['nodes'])

        if 'edges' in dataset and len(dataset['edges']) > 0:
            self.save_docs(self.config()['_EDGE_NAME'], dataset['edges'])


    def save_docs(self, coll_name, docs, on_dupe='update'):

        resp = requests.put(
            self.config()['API_URL'] + '/api/v1/documents',
            params={'collection': coll_name, 'on_duplicate': on_dupe},
            headers={'Authorization': self.config()['AUTH_TOKEN']},
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

