import json
from chemcards.database.resources import (
    CHEMBL_DOWNLOAD,
    CHEMBL_MECHANISM_DOWNLOAD,
    CHEMBL_TARGET_DOWNLOAD,
)
from chemcards.database.core import MoleculeEntry, MoleculeDB
from pydantic import BaseModel


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


def download_drug_mechanisms():
    from chembl_webresource_client.new_client import new_client
    from tqdm import tqdm

    # Get all approved drugs
    approved_drugs = new_client.mechanism.filter(
        max_phase=4,
        molecule_type="Small molecule",
    )
    approved_drugs = [drug for drug in tqdm(approved_drugs)]

    # Save Locally
    with open(CHEMBL_MECHANISM_DOWNLOAD, "w") as f:
        json.dump(approved_drugs, f)


def download_drug_targets():
    from chembl_webresource_client.new_client import new_client
    from tqdm import tqdm

    # Get all approved drugs
    approved_drugs = new_client.target.filter(
        max_phase=4,
        molecule_type="Small molecule",
    )
    approved_drugs = [drug for drug in tqdm(approved_drugs)]

    # Save Locally
    with open(CHEMBL_TARGET_DOWNLOAD, "w") as f:
        json.dump(approved_drugs, f)


class ChemblMoleculeEntry(MoleculeEntry):
    molecule_chembl_id: str
    target_chembl_id: str

    @classmethod
    def from_download(cls, entry) -> "ChemblMoleculeEntry":
        try:
            name = entry["pref_name"]
            smiles = entry["molecule_structures"]["canonical_smiles"]
            target = entry["usan_stem_definition"]
            indication = entry["indication_class"]
            molecule_chembl_id = entry["molecule_chembl_id"]

            if target is None:
                target = "unknown"
            if indication is None:
                indication = "unknown"
            return cls(
                name=name,
                smiles=smiles,
                target=target,
                indication=indication,
                molecule_chembl_id=molecule_chembl_id,
                target_chembl_id="unknown",
            )

        except Exception as e:
            # print(f"Unable to extract a Molecule Object from Chembl entry: {entry}")
            return


class ChemblMechanismEntry(BaseModel):
    molecule_chembl_id: str
    target_chembl_id: str
    mechanism_of_action: str
    action_type: str

    def query_chembl_for_target(self) -> str:
        from chembl_webresource_client.new_client import new_client

        return new_client.target.filter(target_chembl_id=self.target_chembl_id).only(
            "pref_name"
        )[0]["pref_name"]

    def query_chembl_for_molecule(self) -> dict:
        from chembl_webresource_client.new_client import new_client

        return new_client.molecule.filter(molecule_chembl_id=self.molecule_chembl_id)[0]

    @classmethod
    def from_download(cls, entry) -> "ChemblMechanismEntry":

        try:
            return cls(**entry)

        except Exception as e:
            # print(f"Unable to extract a Molecule Object from Chembl entry: {entry}")
            return


class ChemblDB(MoleculeDB):

    @classmethod
    def from_download(cls) -> "ChemblDB":
        with open(CHEMBL_DOWNLOAD, "r") as f:
            molecule_list = json.load(f)

        converted_molecules = [
            ChemblMoleculeEntry.from_download(entry) for entry in molecule_list
        ]
        converted_molecules = [mol for mol in converted_molecules if mol is not None]

        return cls(molecules=converted_molecules)

    @classmethod
    def from_mechanism(cls) -> "ChemblDB":
        from tqdm import tqdm

        with open(CHEMBL_MECHANISM_DOWNLOAD, "r") as f:
            mechanism_list = json.load(f)
        initial_loaded_mechanism = [
            ChemblMechanismEntry.from_download(entry) for entry in mechanism_list
        ]
        filtered_mechanism_list = [m for m in initial_loaded_mechanism if m is not None]

        converted_molecules = []
        for loaded_mechanism in tqdm(filtered_mechanism_list):
            molecule = ChemblMoleculeEntry.from_download(
                loaded_mechanism.query_chembl_for_molecule()
            )
            if molecule is None:
                continue
            converted_molecules.append(
                ChemblMoleculeEntry(
                    name=molecule.name,
                    smiles=molecule.smiles,
                    target=loaded_mechanism.query_chembl_for_target(),
                    indication=molecule.indication,
                    molecule_chembl_id=loaded_mechanism.molecule_chembl_id,
                    target_chembl_id=loaded_mechanism.target_chembl_id,
                    mechanism_of_action=loaded_mechanism.mechanism_of_action,
                    action_type=loaded_mechanism.action_type,
                )
            )
        return cls(molecules=converted_molecules)


def main():

    if not CHEMBL_DOWNLOAD.exists():
        print("Downloading Chembl Molecule Data")
        download_drug_molecules()

    if not CHEMBL_MECHANISM_DOWNLOAD.exists():
        print("Downloading Chembl Mechanism Data")
        download_drug_mechanisms()

    # if not CHEMBL_TARGET_DOWNLOAD.exists():
    #     print("Downloading Chembl Target Data")
    #     download_drug_targets()

    # mydb = ChemblDB.from_download()
    mydb = ChemblDB.from_mechanism()
    mydb.save()


if __name__ == "__main__":
    main()
