"""
Loads the Dan Jacobson/ORNL group's gene and phenotype network data into
arangodb.

Running this requires a set of source files provided by the ORNL group.
"""
from importers.djornl.parser import DJORNL_Parser

if __name__ == '__main__':
    parser = DJORNL_Parser()
    parser.load_data()
