import pytest
from chemcards.database import resources as local_resources

def test_resources():
    assert local_resources.CHEMBL_DOWNLOAD.exists()
