import json
import logging
from chemcards.database.resources import (
    CHEMBL_DOWNLOAD,
    CHEMBL_MECHANISM_DOWNLOAD,
    CHEMBL_TARGET_DOWNLOAD,
)
from chemcards.database.core import MoleculeEntry, MoleculeDB
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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
    def from_download(cls, entry: dict) -> "ChemblMoleculeEntry|None":
        try:
            # Prefer human-readable name, fall back to chembl id
            name = entry.get("pref_name") or entry.get("molecule_chembl_id") or "unknown"

            mol_struct = entry.get("molecule_structures")
            if not mol_struct:
                # No structure recorded for this entry; skip it
                return None
            smiles = mol_struct.get("canonical_smiles")
            if not smiles:
                return None

            target = entry.get("usan_stem_definition") or "unknown"
            molecule_chembl_id = entry.get("molecule_chembl_id") or "unknown"

            return cls(
                name=name,
                smiles=smiles,
                target=target,
                molecule_chembl_id=molecule_chembl_id,
                target_chembl_id="unknown",
            )
        except Exception as e:
            logger.debug("Failed to parse ChemBL molecule entry: %s", e)
            # If anything unexpected happens while parsing, skip this entry
            return None

        # except Exception as e:
        #     # print(f"Unable to extract a Molecule Object from Chembl entry: {entry}")
        #     return


CHEMBL_URL = "https://www.ebi.ac.uk/chembl/compound_report_card/"


def open_chembl_molecule_link(molecule: ChemblMoleculeEntry):
    import webbrowser

    url = CHEMBL_URL + molecule.molecule_chembl_id
    return webbrowser.open_new_tab(url)


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
    def from_download(cls, entry) -> "ChemblMechanismEntry|None":
        try:
            # Normalize parent -> molecule id if present
            parent = entry.get("parent_molecule_chembl_id", None)
            if parent is not None:
                entry["molecule_chembl_id"] = parent

            mol_id = entry.get("molecule_chembl_id")
            target_id = entry.get("target_chembl_id")

            # mechanism_of_action and action_type may be missing; provide sensible defaults
            moa = entry.get("mechanism_of_action") or entry.get("mechanism") or "unknown"
            action = entry.get("action_type") or "unknown"

            # If required identifiers are missing, skip this mechanism entry
            if not mol_id or not target_id:
                return None

            return cls(
                molecule_chembl_id=mol_id,
                target_chembl_id=target_id,
                mechanism_of_action=moa,
                action_type=action,
            )
        except Exception as e:
            logger.debug("Failed to parse ChemBL mechanism entry: %s", e)
            return None

        # except Exception as e:
        #     # print(f"Unable to extract a Molecule Object from Chembl entry: {entry}")
        #     return


class ChemblDB(MoleculeDB):

    @classmethod
    def from_download(cls) -> "ChemblDB":
        with open(CHEMBL_DOWNLOAD, "r") as f:
            molecule_list = json.load(f)

        raw_converted = [ChemblMoleculeEntry.from_download(entry) for entry in molecule_list]
        skipped = sum(1 for x in raw_converted if x is None)
        converted_molecules = [mol for mol in raw_converted if mol is not None]

        logger.info("ChemBL molecules: converted=%d skipped=%d", len(converted_molecules), skipped)

        return cls(molecules=converted_molecules)

    def remove_duplicates(self):
        mol_dict = {mol.name: mol for mol in self.molecules}
        self.molecules = list(mol_dict.values())

    @classmethod
    def from_mechanism(cls) -> "ChemblDB":
        from tqdm import tqdm

        with open(CHEMBL_MECHANISM_DOWNLOAD, "r") as f:
            mechanism_list = json.load(f)
        raw_mechanisms = [ChemblMechanismEntry.from_download(entry) for entry in mechanism_list]
        skipped_mechanisms = sum(1 for x in raw_mechanisms if x is None)
        filtered_mechanism_list = [m for m in raw_mechanisms if m is not None]

        logger.info("ChemBL mechanisms: loaded=%d skipped=%d", len(filtered_mechanism_list), skipped_mechanisms)

        converted_molecules = []
        skipped_molecule_lookups = 0
        skipped_build_failures = 0
        for loaded_mechanism in tqdm(filtered_mechanism_list):
            try:
                mol_dict = loaded_mechanism.query_chembl_for_molecule()
            except Exception as e:
                logger.debug("Failed to query ChemBL for molecule %s: %s", loaded_mechanism.molecule_chembl_id, e)
                skipped_molecule_lookups += 1
                continue

            molecule = ChemblMoleculeEntry.from_download(mol_dict)
            if molecule is None:
                # Could not construct a molecule from the queried data
                skipped_molecule_lookups += 1
                continue
            try:
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
            except Exception as e:
                logger.debug("Failed to build converted molecule from mechanism entry: %s", e)
                skipped_build_failures += 1
                continue

        logger.info(
            "ChemBL mechanism conversion: converted=%d skipped_lookup=%d skipped_build=%d",
            len(converted_molecules),
            skipped_molecule_lookups,
            skipped_build_failures,
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

    mydb = ChemblDB.from_download()
    mydb = ChemblDB.from_mechanism()
    mydb.remove_duplicates()
    mydb.save()


if __name__ == "__main__":
    main()
