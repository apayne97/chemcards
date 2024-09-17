from importlib import resources

DATABASE = resources.files("chemcards") / "database/data"
if not DATABASE.exists():
    DATABASE.mkdir(parents=True)
CHEMBL_DOWNLOAD = DATABASE / "chembl_approved_drugs.json"
MOLECULE_DATABASE = DATABASE / "molecule_database.json"
TEMP_DIR = DATABASE / "temp"
