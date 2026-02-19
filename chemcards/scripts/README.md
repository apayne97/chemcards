# Molecule Catalog Generation

Generate PDF catalogs of functional groups and FDA-approved drugs using RDKit's `MolsToGridImage`.

## Usage

### Generate Combined Catalog

```bash
chemcards generate-catalog
```

Creates: `chemcards/data/catalog_output/molecule_catalog.pdf`

### Generate Separate PDFs

```bash
chemcards generate-catalog --separate
```

Creates:
- `functional_groups.pdf` (21 functional groups)
- `fda_approved_drugs.pdf` (~2000 drugs)

### Options

```bash
chemcards generate-catalog --help
```

- `--no-functional-groups` - Skip functional groups section
- `--no-fda-approved` - Skip FDA drugs section
- `--separate` - Create separate PDFs for each section
- `--out-pdf PATH` - Custom output path (ignored with --separate)
- `--out-dir PATH` - Custom output directory (only with --separate)

### Examples

```bash
# Only functional groups
chemcards generate-catalog --no-fda-approved

# Only FDA drugs  
chemcards generate-catalog --no-functional-groups

# Separate PDFs in custom directory
chemcards generate-catalog --separate --out-dir ~/Desktop/molecules

# Combined PDF with custom name
chemcards generate-catalog --out-pdf ~/Desktop/my_catalog.pdf
```

## Features

- **Fast**: Uses RDKit's optimized grid rendering
- **Simple**: ~100 lines of code, direct PDF output
- **Memory efficient**: Loads all molecules at once but no intermediate files
- **High quality**: RDKit handles all layout and spacing

## Implementation

The catalog generator (`chemcards/scripts/generate_catalog.py`):

1. Loads molecules from YAML (functional groups) and JSON (FDA drugs)
2. Converts to RDKit molecule objects
3. Calls `MolsToGridImage()` to render grid
4. Saves directly to PDF: `grid_img.save("output.pdf", "PDF")`

That's it - no complex canvas drawing, no intermediate images, just clean and simple.
