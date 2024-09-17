from chembl_webresource_client.new_client import new_client
import json
from tqdm import tqdm
from chemcards.database.resources import CHEMBL_DOWNLOAD

def download_drug_molecules():
    # Get all approved drugs
    approved_drugs = new_client.molecule.filter(max_phase=4,
                                                molecule_type='Small molecule',
                                                )
    approved_drugs = [drug for drug in tqdm(approved_drugs)]

    # Save Locally
    with open(CHEMBL_DOWNLOAD, 'w') as f:
        json.dump(approved_drugs, f)

if __name__ == '__main__':
    download_drug_molecules()