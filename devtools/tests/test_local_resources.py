import pytest
from chemcards.database import resources as local_resources


def test_runtime_resources_exist():
    """Files required for the app to run — always committed to the repo."""
    assert local_resources.MOLECULE_DATABASE.exists()
    assert local_resources.FUNCTIONAL_GROUPS_DATABASE.exists()
    assert local_resources.FUNCTIONAL_GROUP_CATEGORIES_DATABASE.exists()


@pytest.mark.skipif(
    not local_resources.CHEMBL_DOWNLOAD.exists(),
    reason="raw ChEMBL downloads not present (dev-only)",
)
def test_chembl_download_resources_exist():
    """Raw ChEMBL files — only present after running the download step locally."""
    assert local_resources.CHEMBL_DOWNLOAD.exists()
    assert local_resources.CHEMBL_MECHANISM_DOWNLOAD.exists()
    assert local_resources.CHEMBL_TARGET_DOWNLOAD.exists()
    assert local_resources.CHEMBL_ATC_DOWNLOAD.exists()
