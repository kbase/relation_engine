import re
from jsonschema.exceptions import ValidationError
from relation_engine_server.utils.json_validation import get_schema_validator
import os
import unittest

cwd = os.path.dirname(os.path.abspath(__file__))
yaml_drpth = os.path.join(cwd, "../../collections/silva")
node_yaml_flpth = os.path.join(yaml_drpth, "silva_taxon.yaml")
edge_yaml_flpth = os.path.join(yaml_drpth, "silva_child_of_taxon.yaml")


class SILVATreeJSONSchemaTest(unittest.TestCase):
    """
    Test the API of the nodes and edges representing SILVA taxonomy tree
    All information is from SILVA (arb-silva.de)
    See their documentation for more details
    """

    @classmethod
    def setUpClass(cls):
        cls.validator_node = get_schema_validator(
            schema_file=node_yaml_flpth, validate_at="/schema"
        )
        cls.validator_edge = get_schema_validator(
            schema_file=edge_yaml_flpth, validate_at="/schema"
        )

        cls.nodes_valid = [
            {
                "id": "0",  # Root's info is assigned by API, since SILVA doesn't seem to have a root node
                "name": "Root",
                "rank": "root_rank",
            },
            {
                "id": "2",
                "name": "Archea",
                "rank": "domain",
            },
            {
                "id": "47023",
                "name": "BCP clade",
                "rank": "major_clade",
                "release": 138,
            },
            {
                "id": "42919",
                "name": "Asgardarchaeota",
                "rank": "phylum",
                "release": 138,
            },
            {
                "id": "4155",
                "name": "Amb-18S-504",
                "rank": "order",
                "release": 119.1,
            },
            {
                "id": "47162",
                "name": "Japygoidea",
                "rank": "superfamily",
                "release": 138,
            },
            {
                "id": "47142",
                "name": "Tantulocarida",
                "rank": "subclass",
                "release": 138,
            },
            {
                "id": "HM032797.1.1344",
                "name": "Yeosuana aromativorans",
                "rank": "sequence",
                "sequence": "gattaca",
                "dataset": ["parc", "ref", "nr99"],
            },
            {
                "id": "CRQV01000019.5091.6588",
                "name": "Streptococcus penumoniae",
                "rank": "sequence",
                "sequence": "gattaca",
                "dataset": ["parc", "ref"],  # actually in nr99
            },
            {
                "id": "HQ216288.1.1242",
                "name": "uncultured bacterium",
                "rank": "sequence",
                "sequence": "gattaca",
                "dataset": ["parc"],  # actually in nr99
            },
        ]

        cls.nodes_invalid_errors = [
            (
                {
                    # missing
                    "id": "id",
                    "name": "name",
                },
                "'rank' is a required property",
            ),
            (
                {
                    # missing
                    "id": "id",
                    "rank": "kingdom",
                },
                "'name' is a required property",
            ),
            (
                {
                    # missing
                    "name": "name",
                    "rank": "major_clade",
                },
                "'id' is a required property",
            ),
            (
                {
                    # type
                    "id": 1,
                    "name": "name",
                    "rank": "subphylum",
                },
                "1 is not of type 'string'",
            ),
            (
                {
                    # type
                    "id": "id",
                    "name": 1,
                    "rank": "subkingdom",
                },
                "1 is not of type 'string'",
            ),
            (
                {
                    # type
                    "id": "id",
                    "name": "name",
                    "rank": 1,
                },
                "1 is not of type 'string'",
            ),
            (
                {
                    # type
                    "id": "id",
                    "name": "name",
                    "rank": "infraphylum",
                    "release": "119",
                },
                "'119' is not of type 'number'",
            ),
            (
                {
                    # type
                    "id": "id",
                    "name": "name",
                    "rank": "sequence",
                    "sequence": 1,
                },
                "1 is not of type 'string'",
            ),
            (
                {
                    # type
                    "id": "id",
                    "name": "name",
                    "rank": "subphylum",
                    "dataset": 1,
                },
                "1 is not of type 'array'",
            ),
            (
                {
                    # enum
                    "id": "id",
                    "name": "name",
                    "rank": "fictional_rank",
                },
                "'fictional_rank' is not one of ['superfamily', 'subphylum', 'subfamily', "
                + "'phylum', 'order', 'major_clade', 'infraclass', 'suborder', 'family', "
                + "'superkingdom', 'domain', 'superphylum', 'superorder', 'superclass', "
                + "'infraphylum', 'subclass', 'genus', 'class', 'kingdom', 'subkingdom', "
                + "'root_rank', 'sequence']",
            ),
            (
                {
                    # enum
                    "id": "id",
                    "name": "name",
                    "rank": "superclass",
                    "dataset": ["nr99", "ref", "parc"],  # array in wrong order
                },
                "['nr99', 'ref', 'parc'] is not one of [['parc'], ['parc', 'ref'], ['parc', 'ref', 'nr99']]",
            ),
        ]

        cls.edges_valid = [
            {
                "id": "2",
                "from": "2",
                "to": "0",
            },
            {
                "id": "42919",
                "from": "42919",
                "to": "2",
            },
            {
                "id": "HM032797.1.1344",
                "from": "HM032797.1.1344",
                "to": "44300",
            },
            {
                "id": "CRQV01000019.5091.6588",
                "from": "CRQV01000019.5091.6588",
                "to": "1853",
            },
        ]

        cls.edges_invalid_errors = [
            (
                {
                    # missing
                    "from": "2",
                    "to": "0",
                },
                "'id' is a required property",
            ),
            (
                {
                    # missing
                    "id": "2",
                    "to": "0",
                },
                "'from' is a required property",
            ),
            (
                {
                    # missing
                    "id": "2",
                    "from": "2",
                },
                "'to' is a required property",
            ),
            (
                {
                    # type
                    "id": 2,
                    "from": "2",
                    "to": "0",
                },
                "2 is not of type 'string'",
            ),
            (
                {
                    # type
                    "id": "2",
                    "from": 2,
                    "to": "0",
                },
                "2 is not of type 'string'",
            ),
            (
                {
                    # type
                    "id": "2",
                    "from": "2",
                    "to": 0,
                },
                "0 is not of type 'string'",
            ),
        ]

    def _test_type(self, validator, insts_valid, insts_invalid_errors):
        for inst in insts_valid:
            with self.subTest(inst=inst):
                validator.validate(inst)

        for inst, err_expected in insts_invalid_errors:
            with self.subTest(inst=inst):
                with self.assertRaisesRegex(
                    ValidationError, "^" + re.escape(err_expected) + "\n"
                ):
                    validator.validate(inst)

    def test(self):
        self._test_type(
            self.validator_node, self.nodes_valid, self.nodes_invalid_errors
        )
        self._test_type(
            self.validator_edge, self.edges_valid, self.edges_invalid_errors
        )


if __name__ == "__main__":
    unittest.main()
