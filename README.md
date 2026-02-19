# ChemCards

A chemistry flashcard application for learning molecular structures, functional groups, and drug information.

## What is ChemCards?

ChemCards is an interactive study tool designed for chemistry students and professionals to learn and memorize:

- **Functional Groups** - Learn to recognize SMARTS patterns and functional group names
- **FDA-Approved Drugs** - Study molecular structures, targets, and mechanisms of action
- **Interactive Quizzes** - Multiple-choice questions with visual molecule rendering

The application uses RDKit for molecule visualization and provides a GUI-based quiz system powered by tkinter/ttkbootstrap.

## Features

- 🧪 **Multiple Quiz Modes**
  - Molecule to Target
  - Molecule to Name
  - Name to Molecule
  - Functional Group (SMARTS) to Name

- 📚 **Comprehensive Database**
  - 21 functional groups with SMARTS patterns
  - ~2000 FDA-approved drugs from ChEMBL
  - Downloadable and updateable molecule database

- 📄 **PDF Catalog Generation**
  - Generate visual catalogs of molecules
  - Separate or combined PDFs for functional groups and drugs
  - Searchable molecule names

## Installation

### Prerequisites

- Python 3.10 or higher
- Conda (recommended) or pip

### Using Conda (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd chemcards

# Create environment from the provided file
conda env create -f devtools/environment.yaml -n chemcards

# Activate the environment
conda activate chemcards

# Install the package in development mode
pip install -e .
```

## Quick Start

### 1. Download the Molecule Database

First, download the FDA-approved drug database from ChEMBL:

```bash
chemcards download-database
```

This will:
- Download FDA-approved small molecules from ChEMBL
- Download mechanism of action data
- Create `chemcards/database/data/molecule_database.json`

**Note:** This may take several minutes and requires an internet connection.

### 2. Start the Quiz Application

Launch the interactive GUI:

```bash
chemcards start
```

This opens the main window where you can select from various quiz modes.

### 3. Generate a Molecule Catalog
Note: You don't need to download the database to generate a catalog of functional groups, but you do need it for the FDA-approved drugs section.

Create a PDF catalog of all molecules:

```bash
# Generate combined catalog (functional groups + FDA drugs)
chemcards generate-catalog

Output files are saved to `chemcards/data/catalog_output/`

## Data Files

The application uses the following data files:

- `database/data/functional_groups.yaml` - Functional group definitions (SMARTS + names)
- `database/data/molecule_database.json` - FDA-approved drugs (auto-generated)
- `database/data/manually_added_molecules.yaml` - Custom molecules
```
