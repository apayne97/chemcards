"""Generate molecule catalog PDF using RDKit's MolsToGridImage.

This approach uses RDKit's built-in grid rendering to save directly to PDF:
- Simple and efficient (~50 lines of code)
- No intermediate image files needed
- Fast execution
- Direct PDF output from RDKit

Best for: most catalog generation use cases.
"""
from pathlib import Path
from itertools import groupby
import json
import logging
from chemcards.database.core import MoleculeDB

try:
    from rdkit import Chem
    from rdkit.Chem import Draw
except Exception:
    Chem = None
    Draw = None

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "database" / "data"
DEFAULT_OUT_DIR = ROOT / "data" / "catalog_output"
MIN_HEAVY_ATOMS = 5
MAX_HEAVY_ATOMS = 29
LIGHT_BLUE_HIGHLIGHT = (68 / 256, 178 / 256, 212 / 256)
HEADER_BG_COLOR = (52, 136, 163)   # darker blue for category header backgrounds
HEADER_TEXT_COLOR = (255, 255, 255)
HEADER_FONT_SIZE = 52
PDF_RESOLUTION_DPI = 300.0
DEFAULT_MOLS_PER_ROW = 4
# Non-square: extra height gives room for 2-line legend (name + smarts)
DEFAULT_IMG_SIZE = (500, 300)
LEGEND_FONT_SIZE = 28
LEGEND_FRACTION = 0.35   # fraction of subImgSize height reserved for legend text
GRID_PADDING = 0.02


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
    """Build a legend for functional-group example entries (name + smarts only; category is a page header)."""
    return f"{item['example_name']}\n{item['name']}\n{item['smarts']}"


def _make_header_image(label: str, width: int) -> "Image.Image":
    """Create a PIL header banner image for a catalog category page."""
    height = HEADER_FONT_SIZE + 40
    img = Image.new("RGB", (width, height), color=HEADER_BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Try a system font at the target size; fall back to PIL's default
    font = None
    for font_name in ["Arial.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttf", "FreeSansBold.ttf"]:
        try:
            font = ImageFont.truetype(font_name, HEADER_FONT_SIZE)
            break
        except (IOError, OSError):
            continue
    if font is None:
        font = ImageFont.load_default()

    # Centre the text horizontally
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    x = max(20, (width - text_w) // 2)
    y = (height - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), label, fill=HEADER_TEXT_COLOR, font=font)
    return img


def _render_grouped_pages(
    items: list[dict],
    mols_per_row: int,
    img_size: tuple,
    legend_fn,
    highlight: bool = False,
    section_label: str | None = None,
) -> list["Image.Image"]:
    """Render a list of molecule items as PIL pages, with a category header per group.

    Args:
        items: list of dicts with at least 'mol', 'category', and legend fields.
        mols_per_row: columns per row in the molecular grid.
        img_size: (width, height) per cell in the grid.
        legend_fn: callable(item) -> legend string.
        highlight: whether items carry highlight_atoms / highlight_bonds.
        section_label: if provided, overrides the per-item category (e.g. for FDA drugs).
    Returns:
        List of PIL Images, one per category group.
    """
    pages = []
    grid_width = mols_per_row * img_size[0]

    if section_label:
        groups = [(section_label, items)]
    else:
        groups = [
            (cat, list(grp))
            for cat, grp in groupby(items, key=lambda x: x["category"])
        ]

    for category, group_items in groups:
        mols    = [item["mol"] for item in group_items]
        legends = [legend_fn(item) for item in group_items]
        h_atoms = [item.get("highlight_atoms", tuple()) for item in group_items] if highlight else None
        h_bonds = [item.get("highlight_bonds", tuple()) for item in group_items] if highlight else None

        kwargs = dict(
            molsPerRow=mols_per_row,
            subImgSize=img_size,
            legends=legends,
            drawOptions=_catalog_draw_options(),
            returnPNG=False,
        )
        if highlight:
            kwargs["highlightAtomLists"] = h_atoms
            kwargs["highlightBondLists"] = h_bonds

        grid_img = Draw.MolsToGridImage(mols, **kwargs)

        # Resize header to match the grid's actual rendered width
        actual_width = grid_img.width
        header_img = _make_header_image(category.replace("_", " ").upper(), actual_width)

        page = Image.new("RGB", (actual_width, header_img.height + grid_img.height), (255, 255, 255))
        page.paste(header_img, (0, 0))
        page.paste(grid_img, (0, header_img.height))
        pages.append(page)

    return pages


def _save_pages_as_pdf(pages: list["Image.Image"], out_pdf: Path) -> None:
    """Save a list of PIL images as a multi-page PDF."""
    if not pages:
        return
    pages[0].save(
        str(out_pdf),
        "PDF",
        resolution=PDF_RESOLUTION_DPI,
        save_all=True,
        append_images=pages[1:],
    )


def _load_category_order(categories_yaml_path: Path) -> list[str]:
    """Load the preferred category display order from YAML.

    Categories are stored as human-readable strings (spaces, lowercase).
    Returns a list in preferred order; unknown categories sort last.
    """
    import yaml
    if not categories_yaml_path.exists():
        return []
    with categories_yaml_path.open("r", encoding="utf8") as fh:
        return [str(c) for c in (yaml.safe_load(fh) or [])]


def _load_functional_groups(yaml_path: Path):
    """Load functional group definitions from YAML file."""
    import yaml
    if not yaml_path.exists():
        return []
    with yaml_path.open("r", encoding="utf8") as fh:
        data = yaml.safe_load(fh) or []

    # Load preferred category order (normalise both sides to space-separated lowercase).
    categories_path = yaml_path.parent / "functional_group_categories.yaml"
    category_order = _load_category_order(categories_path)
    # Map normalised category string -> sort index; unknowns go last.
    category_rank = {c.lower(): i for i, c in enumerate(category_order)}

    def _sort_key(item):
        raw = (item.get("category") or "uncategorized").replace("_", " ").lower()
        return (category_rank.get(raw, len(category_order)), (item.get("name") or "unknown").casefold())

    data = sorted(data, key=_sort_key)

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

    all_pages = []

    if funcs:
        all_pages.extend(_render_grouped_pages(
            funcs, mols_per_row, img_size,
            legend_fn=_format_functional_group_legend,
            highlight=True,
        ))

    if drugs:
        all_pages.extend(_render_grouped_pages(
            drugs, mols_per_row, img_size,
            legend_fn=lambda item: item["name"],
            highlight=False,
            section_label="FDA APPROVED DRUGS",
        ))

    logging.info("Rendering %d pages to PDF...", len(all_pages))
    _save_pages_as_pdf(all_pages, out_pdf)

    logging.info("PDF saved: %s (%d pages)", out_pdf, len(all_pages))
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

    # Functional Groups PDF — one page per category, each with a header
    if functional_groups:
        funcs = _load_functional_group_examples(yaml_path)
        if funcs:
            logging.info("Rendering %d functional groups...", len(funcs))
            pages = _render_grouped_pages(
                funcs, mols_per_row, img_size,
                legend_fn=_format_functional_group_legend,
                highlight=True,
            )
            fg_pdf = out_dir / "functional_groups.pdf"
            _save_pages_as_pdf(pages, fg_pdf)
            logging.info("Saved: %s (%d pages)", fg_pdf, len(pages))
            results.append(fg_pdf)

    # FDA Approved Drugs PDF — single section header
    if fda_approved:
        drugs = _load_approved_drugs(json_path)
        if drugs:
            logging.info("Rendering %d FDA-approved drugs...", len(drugs))
            pages = _render_grouped_pages(
                drugs, mols_per_row, img_size,
                legend_fn=lambda item: item["name"],
                highlight=False,
                section_label="FDA APPROVED DRUGS",
            )
            drugs_pdf = out_dir / "fda_approved_drugs.pdf"
            _save_pages_as_pdf(pages, drugs_pdf)
            logging.info("Saved: %s (%d pages)", drugs_pdf, len(pages))
            results.append(drugs_pdf)

    return results


if __name__ == "__main__":
    # Generate separate PDFs for each section
    generate_catalog_sections()
