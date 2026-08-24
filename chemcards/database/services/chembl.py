import json
import logging
from chemcards.database.resources import (
    CHEMBL_DOWNLOAD,
    CHEMBL_MECHANISM_DOWNLOAD,
    CHEMBL_TARGET_DOWNLOAD,
    CHEMBL_ATC_DOWNLOAD,
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
    """Fetch pref_name for every target referenced in the mechanism download.

    Saves a dict {target_chembl_id: pref_name} rather than raw records.
    Requires CHEMBL_MECHANISM_DOWNLOAD to already exist.
    """
    from chembl_webresource_client.new_client import new_client

    with open(CHEMBL_MECHANISM_DOWNLOAD) as f:
        mechanisms = json.load(f)

    unique_ids = list({m["target_chembl_id"] for m in mechanisms if m.get("target_chembl_id")})

    # Chunk to avoid hitting URL length limits on the ChEMBL REST API
    chunk_size = 100
    target_dict: dict = {}
    for i in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[i : i + chunk_size]
        records = new_client.target.filter(target_chembl_id__in=chunk).only(
            ["target_chembl_id", "pref_name"]
        )
        for record in records:
            target_dict[record["target_chembl_id"]] = record["pref_name"]

    logger.info("Fetched names for %d/%d targets.", len(target_dict), len(unique_ids))
    with open(CHEMBL_TARGET_DOWNLOAD, "w") as f:
        json.dump(target_dict, f)


def download_atc_classes() -> None:
    """Download ATC hierarchy from ChEMBL and save a {code: description} lookup.

    Covers all four levels so stats can group at any granularity.
    Saves e.g. {"L": "Antineoplastic...", "L01": "Antineoplastic agents",
                 "L01E": "Protein kinase inhibitors", "L01ED": "BCR-ABL..."}.
    """
    from chembl_webresource_client.new_client import new_client
    from tqdm import tqdm

    records = [r for r in tqdm(new_client.atc_class.all())]

    atc_lookup: dict[str, str] = {}
    for r in records:
        for level in range(1, 5):
            code = r.get(f"level{level}")
            desc = r.get(f"level{level}_description")
            if code and desc:
                atc_lookup[code] = desc.title()

    logger.info("ATC lookup: %d entries across 4 levels.", len(atc_lookup))
    with open(CHEMBL_ATC_DOWNLOAD, "w") as f:
        json.dump(atc_lookup, f)


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
            atc_classifications = entry.get("atc_classifications") or []

            return cls(
                name=name,
                smiles=smiles,
                target=target,
                molecule_chembl_id=molecule_chembl_id,
                target_chembl_id="unknown",
                atc_classifications=atc_classifications,
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
        """Build a ChemblDB by joining local mechanism, molecule, and target files.

        No API calls — pure local JSON lookups.
        """
        with open(CHEMBL_DOWNLOAD) as f:
            mol_lookup: dict = {
                m["molecule_chembl_id"]: m
                for m in json.load(f)
                if m.get("molecule_chembl_id")
            }

        with open(CHEMBL_TARGET_DOWNLOAD) as f:
            target_lookup: dict = json.load(f)  # {target_chembl_id: pref_name}

        with open(CHEMBL_MECHANISM_DOWNLOAD) as f:
            mechanism_list = json.load(f)

        raw_mechanisms = [ChemblMechanismEntry.from_download(entry) for entry in mechanism_list]
        filtered_mechanisms = [m for m in raw_mechanisms if m is not None]
        logger.info("ChemBL mechanisms: parsed=%d skipped=%d",
                    len(filtered_mechanisms), len(raw_mechanisms) - len(filtered_mechanisms))

        converted_molecules = []
        skipped = 0
        for mech in filtered_mechanisms:
            mol_dict = mol_lookup.get(mech.molecule_chembl_id)
            if mol_dict is None:
                skipped += 1
                continue

            molecule = ChemblMoleculeEntry.from_download(mol_dict)
            if molecule is None:
                skipped += 1
                continue

            target_name = target_lookup.get(mech.target_chembl_id, "unknown")
            usan_stem = mol_dict.get("usan_stem_definition") or "unknown"
            converted_molecules.append(
                ChemblMoleculeEntry(
                    name=molecule.name,
                    smiles=molecule.smiles,
                    target=target_name,
                    usan_stem_definition=usan_stem,
                    indication=molecule.indication,
                    molecule_chembl_id=mech.molecule_chembl_id,
                    target_chembl_id=mech.target_chembl_id,
                    mechanism_of_action=mech.mechanism_of_action,
                    action_type=mech.action_type,
                    atc_classifications=molecule.atc_classifications,
                )
            )

        logger.info("ChemBL mechanism conversion: converted=%d skipped=%d",
                    len(converted_molecules), skipped)
        return cls(molecules=converted_molecules)


def download_raw_data(force: bool = False) -> None:
    """Download raw ChEMBL molecule, mechanism, and target data to local JSON files.

    Skips files that already exist unless force=True.
    Target download requires mechanism data to be present first.
    """
    if force or not CHEMBL_DOWNLOAD.exists():
        logger.info("Downloading ChEMBL molecule data...")
        download_drug_molecules()
    else:
        logger.info("ChEMBL molecule data already cached, skipping download.")

    if force or not CHEMBL_MECHANISM_DOWNLOAD.exists():
        logger.info("Downloading ChEMBL mechanism data...")
        download_drug_mechanisms()
    else:
        logger.info("ChEMBL mechanism data already cached, skipping download.")

    if force or not CHEMBL_TARGET_DOWNLOAD.exists():
        logger.info("Fetching ChEMBL target names...")
        download_drug_targets()
    else:
        logger.info("ChEMBL target data already cached, skipping download.")

    if force or not CHEMBL_ATC_DOWNLOAD.exists():
        logger.info("Fetching ChEMBL ATC class hierarchy...")
        download_atc_classes()
    else:
        logger.info("ChEMBL ATC data already cached, skipping download.")


def build_molecule_database() -> None:
    """Build molecule_database.json by joining cached raw ChEMBL files. No API calls."""
    from datetime import datetime, timezone

    logger.info("Building molecule database...")
    mydb = ChemblDB.from_mechanism()
    mydb.remove_duplicates()
    mydb.last_updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    mydb.save()
    logger.info("Done. %d molecules written to database.", len(mydb.molecules))


def main():
    download_raw_data()
    build_molecule_database()


if __name__ == "__main__":
    main()
