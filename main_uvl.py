import argparse
import pathlib

from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.configuration_metamodel.transformations import (
    ConfigurationJSONReader, 
    UVLSJSONReader
)
from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat
from flamapy.metamodels.pysat_metamodel.operations import (
    PySATSatisfiable,
    PySATSatisfiableConfiguration
)


FM_MODEL_PATH = 'uvl_models/base.uvl'


def main(feature_model_path: str) -> None:
    fm = UVLReader(feature_model_path).transform()
    print(fm)


if __name__ == "__main__":
    main(FM_MODEL_PATH)