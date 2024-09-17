from pathlib import Path
from importlib import resources 
DATABASE = resources.files('chemcards') / 'database/data'
CHEMBL_DOWNLOAD = DATABASE / 'chembl_approved_drugs.json'
MOLECULE_DATABASE = DATABASE / 'molecule_database.json'
TEMP_DIR = DATABASE / 'temp'