from yaml import safe_load
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import os
import unittest

cwd = os.path.dirname(os.path.abspath(__file__))
node_yaml_flpth = os.path.join('..', 'silva_taxon.yaml')
edge_yaml_flpth = os.path.join('..', 'silva_child_of_taxon.yaml')

class SILVATreeJSONSchemaTest(unittest.TestCase):
    '''
    Test the API of the nodes and edges representing SILVA taxonomy tree
    All information is from SILVA (arb-silva.de)
    See their documentation for more details
    '''

    @classmethod
    def setUpClass(cls):
        with open(node_yaml_flpth) as fh:
            cls.schema_node = safe_load(fh)['schema']
        with open(edge_yaml_flpth) as fh:
            cls.schema_edge = safe_load(fh)['schema']

        cls.nodes_valid = [
            {
                'id': '0', # Root's info is assigned by API, since SILVA doesn't seem to have a root node
                'name': 'Root',
                'rank': 'root_rank',
            },{
                'id': '2',
                'name': 'Archea',
                'rank': 'domain',
            },{
                'id': '47023',
                'name': 'BCP clade',
                'rank': 'major_clade',
                'release': 138,
            },{
                'id': '42919',
                'name': 'Asgardarchaeota',
                'rank': 'phylum',
                'release': 138,
            },{
                'id': '4155',
                'name': 'Amb-18S-504',
                'rank': 'order',
                'release': 119.1,
            },{
                'id': '47162',
                'name': 'Japygoidea',
                'rank': 'superfamily',
                'release': 138,
            },{
                'id': '47142',
                'name': 'Tantulocarida',
                'rank': 'subclass',
                'release': 138,
            },{
                'id': 'HM032797.1.1344',
                'name': 'Yeosuana aromativorans',
                'rank': 'sequence',
                'sequence': 'gattaca',
                'dataset': ['parc', 'ref', 'nr99']
            },{
                'id': 'CRQV01000019.5091.6588',
                'name': 'Streptococcus penumoniae',
                'rank': 'sequence',
                'sequence': 'gattaca',
                'dataset': ['parc', 'ref'], # actually in nr99
            },{
                'id': 'HQ216288.1.1242',
                'name': 'uncultured bacterium',
                'rank': 'sequence',
                'sequence': 'gattaca',
                'dataset': ['parc'], # actually in nr99
            }
        ]

        cls.nodes_invalid = [
            {
                # missing
                'id': 'id',
                'name': 'name',
            },{
                # missing
                'id': 'id',
                'rank': 'kingdom',
            },{
                # missing
                'name': 'name',
                'rank': 'major_clade',
            },{
                # type
                'id': 1,
                'name': 'name',
                'rank': 'subphylum',
            },{
                # type
                'id': 'id',
                'name': 1,
                'rank': 'subkingdom',
            },{
                # type
                'id': 'id',
                'name': 'name',
                'rank': 1,
            },{
                # type
                'id': 'id',
                'name': 'name',
                'rank': 'infraphylum',
                'release': '119',
            },{
                # type
                'id': 'id',
                'name': 'name',
                'rank': 'sequence',
                'sequence': 1,
            },{
                # type
                'id': 'id',
                'name': 'name',
                'rank': 'subphylum',
                'dataset': 1,
            },{
                # enum
                'id': 'id',
                'name': 'name',
                'rank': 'fictional_rank',
            },{
                # enum
                'id': 'id',
                'name': 'name',
                'rank': 'superclass',
                'dataset': ['nr99', 'ref', 'parc'], # array in wrong order
            }
        ]

        cls.nodes_errors = [
            "'rank' is a required property",
            "'name' is a required property",
            "'id' is a required property",
            "1 is not of type 'string'",
            "1 is not of type 'string'",
            "1 is not of type 'string'",
            "'119' is not of type 'number'",
            "1 is not of type 'string'",
            "1 is not of type 'array'",
            "'fictional_rank' is not one of ['superfamily', 'subphylum', 'subfamily', 'phylum', 'order', 'major_clade', 'infraclass', 'suborder', 'family', 'superkingdom', 'domain', 'superphylum', 'superorder', 'superclass', 'infraphylum', 'subclass', 'genus', 'class', 'kingdom', 'subkingdom', 'root_rank', 'sequence']",
            "['nr99', 'ref', 'parc'] is not one of [['parc'], ['parc', 'ref'], ['parc', 'ref', 'nr99']]",
        ]

        cls.edges_valid = [
            {
                'id': '2',
                'from': '2',
                'to': '0',
            },{
                'id': '42919',
                'from': '42919',
                'to': '2',
            },{
                'id': 'HM032797.1.1344',
                'from': 'HM032797.1.1344',
                'to': '44300',
            },{
                'id': 'CRQV01000019.5091.6588',
                'from': 'CRQV01000019.5091.6588',
                'to': '1853',
            },
        ]

        cls.edges_invalid = [
            {
                # missing
                'from': '2',
                'to': '0',
            },{
                # missing
                'id': '2',
                'to': '0',
            },{
                # missing
                'id': '2',
                'from': '2',
            },{
                # type
                'id': 2,
                'from': '2',
                'to': '0',
            },{
                # type
                'id': '2',
                'from': 2,
                'to': '0',
            },{
                # type
                'id': '2',
                'from': '2',
                'to': 0,
            },

        ]

        cls.edges_errors = [
            "'id' is a required property",
            "'from' is a required property",
            "'to' is a required property",
            "2 is not of type 'string'",
            "2 is not of type 'string'",
            "0 is not of type 'string'",
        ]

    
    def _test_type(self, schema, valid, invalid, errors=None):
        for inst in valid:
            validate(inst, schema=schema)

        for inst, error in zip(invalid, errors):
            with self.assertRaises(ValidationError) as cm:
                validate(inst, schema=schema)
            msg = str(cm.exception).split('\n')[0]
            
            print(msg)
            self.assertTrue(msg == error, '`%s` vs `%s`' % (msg, str(cm.exception)))


    def test(self):
        self._test_type(self.schema_node, self.nodes_valid, self.nodes_invalid, self.nodes_errors)
        self._test_type(self.schema_edge, self.edges_valid, self.edges_invalid, self.edges_errors)


if __name__ == '__main__':
    unittest.main()
