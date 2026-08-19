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
from chemcards.database.core import MoleculeDB

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
MIN_HEAVY_ATOMS = 5
MAX_HEAVY_ATOMS = 29
LIGHT_BLUE_HIGHLIGHT = (68 / 256, 178 / 256, 212 / 256)
PDF_RESOLUTION_DPI = 300.0
DEFAULT_MOLS_PER_ROW = 4
# Non-square: extra height gives room for 3-line legend
DEFAULT_IMG_SIZE = (500, 300)
LEGEND_FONT_SIZE = 28
LEGEND_FRACTION = 0.35   # fraction of subImgSize height reserved for legend text
GRID_PADDING = 0.00


def _catalog_draw_options():
    """Draw options for catalog output with light-blue substructure highlights."""
    dopts = Draw.rdMolDraw2D.MolDrawOptions()
    dopts.setHighlightColour(LIGHT_BLUE_HIGHLIGHT)
    dopts.highlightBondWidthMultiplier = 20
    dopts.legendFontSize = LEGEND_FONT_SIZE
    dopts.maxFontSize = LEGEND_FONT_SIZE   # must match legendFontSize, otherwise RDKit caps it
    dopts.legendFraction = LEGEND_FRACTION
    dopts.padding = GRID_PADDING
    return dopts


def _format_functional_group_legend(item: dict) -> str:
    """Build a multiline legend for functional-group example entries."""
    category = item["category"].replace("_", " ").capitalize()
    return (f"{category}"
            f"\n{item['name']}"
            # f"\n{item['smarts']}"
            )


def _load_functional_groups(yaml_path: Path):
    """Load functional group definitions from YAML file."""
    import yaml
    if not yaml_path.exists():
        return []
    with yaml_path.open("r", encoding="utf8") as fh:
        data = yaml.safe_load(fh) or []

    # Keep catalog output stable and grouped: category first, then name.
    data = sorted(
        data,
        key=lambda item: (
            (item.get("category") or "uncategorized").casefold(),
            (item.get("name") or "unknown").casefold(),
        ),
    )

    groups = []
    for item in data:
        name = item.get("name") or "unknown"
        category = item.get("category") or "uncategorized"
        smarts = item.get("smarts")
        if smarts:
            patt = Chem.MolFromSmarts(smarts) if Chem else None
            if patt:
                groups.append(
                    {
                        "name": name,
                        "category": category,
                        "smarts": smarts,
                        "pattern": patt,
                    }
                )
    return groups


def _load_functional_group_examples(yaml_path: Path):
    """Load one highlighted molecule example per functional group.

    Each entry contains:
    - name/category
    - mol: a molecule from MoleculeDB containing the SMARTS pattern
    - highlight: atom indices for the matched SMARTS substructure
    """
    groups = _load_functional_groups(yaml_path)
    molecule_db = MoleculeDB.load()
    examples = []
    missing = 0

    candidate_molecules = []
    for molecule in molecule_db.molecules:
        rmol = molecule.to_rdkit()
        if not rmol:
            continue
        heavy_atoms = rmol.GetNumHeavyAtoms()
        if MIN_HEAVY_ATOMS <= heavy_atoms <= MAX_HEAVY_ATOMS:
            candidate_molecules.append((molecule, rmol))

    logging.info(
        "Functional-group example candidates after heavy-atom prefilter (%d-%d): %d",
        MIN_HEAVY_ATOMS,
        MAX_HEAVY_ATOMS,
        len(candidate_molecules),
    )

    for fg in groups:
        pattern = fg["pattern"]
        match_entry = None
        for molecule, rmol in candidate_molecules:
            if rmol.HasSubstructMatch(pattern):
                highlight_atoms = rmol.GetSubstructMatch(pattern)
                if highlight_atoms:
                    highlight_bonds = []
                    for bond in pattern.GetBonds():
                        begin = highlight_atoms[bond.GetBeginAtomIdx()]
                        end = highlight_atoms[bond.GetEndAtomIdx()]
                        match_bond = rmol.GetBondBetweenAtoms(begin, end)
                        if match_bond is not None:
                            highlight_bonds.append(match_bond.GetIdx())

                    match_entry = {
                        "name": fg["name"],
                        "category": fg["category"],
                        "smarts": fg["smarts"],
                        "mol": rmol,
                        "highlight_atoms": highlight_atoms,
                        "highlight_bonds": tuple(highlight_bonds),
                        "example_name": molecule.name,
                    }
                    break

        if match_entry is None:
            missing += 1
            logging.warning("No example molecule found for functional group: %s", fg["name"])
            continue

        examples.append(match_entry)

    if missing:
        logging.info("Skipped %d functional groups with no example match", missing)

    return examples


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
    mols_per_row: int = DEFAULT_MOLS_PER_ROW,
    img_size: tuple = DEFAULT_IMG_SIZE,
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
    funcs = _load_functional_group_examples(yaml_path) if functional_groups else []
    drugs = _load_approved_drugs(json_path) if fda_approved else []

    if not funcs and not drugs:
        logging.warning("No molecules to generate")
        return None

    logging.info("Generating PDF with %d functional groups, %d drugs", len(funcs), len(drugs))

    # Combine all molecules and legends
    all_mols = []
    all_legends = []
    all_highlight_atoms = []
    all_highlight_bonds = []

    if funcs:
        all_mols.extend([item["mol"] for item in funcs])
        all_legends.extend([_format_functional_group_legend(item) for item in funcs])
        all_highlight_atoms.extend([item["highlight_atoms"] for item in funcs])
        all_highlight_bonds.extend([item["highlight_bonds"] for item in funcs])

    if drugs:
        all_mols.extend([item["mol"] for item in drugs])
        all_legends.extend([item["name"] for item in drugs])
        all_highlight_atoms.extend([tuple() for _ in drugs])
        all_highlight_bonds.extend([tuple() for _ in drugs])

    # Generate grid and save directly to PDF
    logging.info("Rendering %d molecules to PDF...", len(all_mols))

    grid_img = Draw.MolsToGridImage(
        all_mols,
        molsPerRow=mols_per_row,
        subImgSize=img_size,
        legends=all_legends,
        highlightAtomLists=all_highlight_atoms,
        highlightBondLists=all_highlight_bonds,
        drawOptions=_catalog_draw_options(),
        returnPNG=False  # Return PIL Image instead of PNG bytes
    )

    # Save directly as PDF
    grid_img.save(str(out_pdf), "PDF", resolution=PDF_RESOLUTION_DPI)

    logging.info("PDF saved: %s (%d molecules)", out_pdf, len(all_mols))
    return out_pdf


def generate_catalog_sections(
    out_dir: Path | str | None = None,
    functional_groups: bool = True,
    fda_approved: bool = True,
    mols_per_row: int = DEFAULT_MOLS_PER_ROW,
    img_size: tuple = DEFAULT_IMG_SIZE,
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
        funcs = _load_functional_group_examples(yaml_path)
        if funcs:
            logging.info("Rendering %d functional groups...", len(funcs))
            mols = [item["mol"] for item in funcs]
            legends = [_format_functional_group_legend(item) for item in funcs]
            highlight_atoms = [item["highlight_atoms"] for item in funcs]
            highlight_bonds = [item["highlight_bonds"] for item in funcs]

            grid_img = Draw.MolsToGridImage(
                mols,
                molsPerRow=mols_per_row,
                subImgSize=img_size,
                legends=legends,
                highlightAtomLists=highlight_atoms,
                highlightBondLists=highlight_bonds,
                drawOptions=_catalog_draw_options(),
                returnPNG=False
            )

            fg_pdf = out_dir / "functional_groups.pdf"
            grid_img.save(str(fg_pdf), "PDF", resolution=PDF_RESOLUTION_DPI)
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
                drawOptions=_catalog_draw_options(),
                returnPNG=False
            )

            drugs_pdf = out_dir / "fda_approved_drugs.pdf"
            grid_img.save(str(drugs_pdf), "PDF", resolution=PDF_RESOLUTION_DPI)
            logging.info("Saved: %s", drugs_pdf)
            results.append(drugs_pdf)

    return results


if __name__ == "__main__":
    # Generate separate PDFs for each section
    generate_catalog_sections()
