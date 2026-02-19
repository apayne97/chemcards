"""Generate molecule catalog PDF using RDKit's MolsToGridImage.

This approach uses RDKit's built-in grid rendering to save directly to PDF:
- Simple and efficient (~50 lines of code)
- No intermediate image files needed
- Fast execution
- Direct PDF output from RDKit

Best for: most catalog generation use cases.
"""
from pathlib import Path
import json
import logging

try:
    from rdkit import Chem
    from rdkit.Chem import Draw
except Exception:
    Chem = None
    Draw = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "database" / "data"
DEFAULT_OUT_DIR = ROOT / "data" / "catalog_output"


def _load_functional_groups(yaml_path: Path):
    """Load functional group definitions from YAML file."""
    import yaml
    if not yaml_path.exists():
        return []
    with yaml_path.open("r", encoding="utf8") as fh:
        data = yaml.safe_load(fh) or []
    groups = []
    for item in data:
        name = item.get("name") or "unknown"
        smarts = item.get("smarts")
        if smarts:
            mol = Chem.MolFromSmarts(smarts) if Chem else None
            if mol:
                groups.append({"name": name, "mol": mol})
    return groups


def _load_approved_drugs(json_path: Path):
    """Load FDA-approved drug molecules from ChEMBL JSON file."""
    if not json_path.exists():
        return []
    with json_path.open("r", encoding="utf8") as fh:
        data = json.load(fh) or []
    drugs = []
    for entry in data:
        smiles = entry.get("canonical_smiles") or entry.get("smiles")
        name = entry.get("pref_name") or entry.get("molecule_chembl_id") or "unknown"
        if smiles:
            mol = Chem.MolFromSmiles(smiles) if Chem else None
            if mol:
                drugs.append({"name": name, "mol": mol})
    return drugs


def generate_catalog(
    out_pdf: Path | str | None = None,
    functional_groups: bool = True,
    fda_approved: bool = True,
    mols_per_row: int = 4,
    img_size: tuple = (250, 250),
):
    """Generate molecule catalog PDF using RDKit's MolsToGridImage.

    Args:
        out_pdf: Output PDF path (defaults to chemcards/data/catalog_output/molecule_catalog.pdf)
        functional_groups: Include functional groups section
        fda_approved: Include FDA-approved molecules section
        mols_per_row: Number of molecules per row in grid
        img_size: Tuple of (width, height) for each molecule image

    Returns:
        Path to generated PDF, or None if nothing was generated
    """
    if Chem is None or Draw is None:
        logging.error("RDKit is required for this function")
        return None

    DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_pdf = Path(out_pdf) if out_pdf else DEFAULT_OUT_DIR / "molecule_catalog.pdf"

    yaml_path = DATA_DIR / "functional_groups.yaml"
    json_path = DATA_DIR / "chembl_approved_drugs.json"

    # Load data
    funcs = _load_functional_groups(yaml_path) if functional_groups else []
    drugs = _load_approved_drugs(json_path) if fda_approved else []

    if not funcs and not drugs:
        logging.warning("No molecules to generate")
        return None

    logging.info("Generating PDF with %d functional groups, %d drugs", len(funcs), len(drugs))

    # Combine all molecules and legends
    all_mols = []
    all_legends = []

    if funcs:
        all_mols.extend([item["mol"] for item in funcs])
        all_legends.extend([item["name"] for item in funcs])

    if drugs:
        all_mols.extend([item["mol"] for item in drugs])
        all_legends.extend([item["name"] for item in drugs])

    # Generate grid and save directly to PDF
    logging.info("Rendering %d molecules to PDF...", len(all_mols))

    grid_img = Draw.MolsToGridImage(
        all_mols,
        molsPerRow=mols_per_row,
        subImgSize=img_size,
        legends=all_legends,
        returnPNG=False  # Return PIL Image instead of PNG bytes
    )

    # Save directly as PDF
    grid_img.save(str(out_pdf), "PDF", resolution=100.0)

    logging.info("PDF saved: %s (%d molecules)", out_pdf, len(all_mols))
    return out_pdf


def generate_catalog_sections(
    out_dir: Path | str | None = None,
    functional_groups: bool = True,
    fda_approved: bool = True,
    mols_per_row: int = 4,
    img_size: tuple = (250, 250),
):
    """Generate separate PDF files for each section.

    This creates:
    - functional_groups.pdf (if functional_groups=True)
    - fda_approved_drugs.pdf (if fda_approved=True)

    Args:
        out_dir: Output directory (defaults to chemcards/data/catalog_output)
        functional_groups: Include functional groups section
        fda_approved: Include FDA-approved molecules section
        mols_per_row: Number of molecules per row in grid
        img_size: Tuple of (width, height) for each molecule image

    Returns:
        List of paths to generated PDFs
    """
    if Chem is None or Draw is None:
        logging.error("RDKit is required for this function")
        return []

    out_dir = Path(out_dir) if out_dir else DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    yaml_path = DATA_DIR / "functional_groups.yaml"
    json_path = DATA_DIR / "chembl_approved_drugs.json"

    results = []

    # Functional Groups PDF
    if functional_groups:
        funcs = _load_functional_groups(yaml_path)
        if funcs:
            logging.info("Rendering %d functional groups...", len(funcs))
            mols = [item["mol"] for item in funcs]
            legends = [item["name"] for item in funcs]

            grid_img = Draw.MolsToGridImage(
                mols,
                molsPerRow=mols_per_row,
                subImgSize=img_size,
                legends=legends,
                returnPNG=False
            )

            fg_pdf = out_dir / "functional_groups.pdf"
            grid_img.save(str(fg_pdf), "PDF", resolution=100.0)
            logging.info("Saved: %s", fg_pdf)
            results.append(fg_pdf)

    # FDA Approved Drugs PDF
    if fda_approved:
        drugs = _load_approved_drugs(json_path)
        if drugs:
            logging.info("Rendering %d FDA-approved drugs...", len(drugs))
            mols = [item["mol"] for item in drugs]
            legends = [item["name"] for item in drugs]

            grid_img = Draw.MolsToGridImage(
                mols,
                molsPerRow=mols_per_row,
                subImgSize=img_size,
                legends=legends,
                returnPNG=False
            )

            drugs_pdf = out_dir / "fda_approved_drugs.pdf"
            grid_img.save(str(drugs_pdf), "PDF", resolution=100.0)
            logging.info("Saved: %s", drugs_pdf)
            results.append(drugs_pdf)

    return results


if __name__ == "__main__":
    # Generate separate PDFs for each section
    generate_catalog_sections()
