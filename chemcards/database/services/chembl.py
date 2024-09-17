import json
from chemcards.database.resources import CHEMBL_DOWNLOAD
from chemcards.database.core import MoleculeEntry, MoleculeDB
from warnings import warn


def download_drug_molecules():
    from chembl_webresource_client.new_client import new_client
    from tqdm import tqdm

    # Get all approved drugs
    approved_drugs = new_client.molecule.filter(
        max_phase=4,
        molecule_type="Small molecule",
    )
    approved_drugs = [drug for drug in tqdm(approved_drugs)]

    # Save Locally
    with open(CHEMBL_DOWNLOAD, "w") as f:
        json.dump(approved_drugs, f)


class ChemblMoleculeEntry(MoleculeEntry):

    @classmethod
    def from_download(cls, entry) -> "ChemblMoleculeEntry":
        try:
            name = entry["pref_name"]
            smiles = entry["molecule_structures"]["canonical_smiles"]
            target = entry["usan_stem_definition"]
            indication = entry["indication_class"]

            if target is None:
                target = "unknown"
            if indication is None:
                indication = "unknown"
            return cls(name=name, smiles=smiles, target=target, indication=indication)

        except Exception as e:
            print(f"Unable to extract a Molecule Object from Chembl entry: {entry}")
            return


class ChemblDB(MoleculeDB):

    @classmethod
    def from_download(cls) -> "ChemblDB":
        with open(CHEMBL_DOWNLOAD, "r") as f:
            molecule_list = json.load(f)

        converted_molecues = [
            ChemblMoleculeEntry.from_download(entry) for entry in molecule_list
        ]
        converted_molecues = [mol for mol in converted_molecues if mol is not None]

        return MoleculeDB(molecules=converted_molecues)


def main():

    if not CHEMBL_DOWNLOAD.exists():
        download_drug_molecules()
    mydb = ChemblDB.from_download()
    mydb.save()


if __name__ == "__main__":
    main()
