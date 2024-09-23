from importlib import resources

DATABASE = resources.files("chemcards") / "database/data"
if not DATABASE.exists():
    DATABASE.mkdir(parents=True)
CHEMBL_DOWNLOAD = DATABASE / "chembl_approved_drugs.json"
CHEMBL_MECHANISM_DOWNLOAD = DATABASE / "chembl_mechanism_approved_drugs.json"
CHEMBL_TARGET_DOWNLOAD = DATABASE / "chembl_target_approved_drugs.json"
MOLECULE_DATABASE = DATABASE / "molecule_database.json"
TEMP_DIR = DATABASE / "temp"
FUNCTIONAL_GROUPS = DATABASE / "functional_groups.yaml"
