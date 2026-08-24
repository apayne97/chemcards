import click


@click.group()
def cli():
    """ChemCards — chemistry flashcard app and database tools."""


@cli.command()
def start():
    """Launch the tkinter GUI."""
    from chemcards.gui.mainwindow import MainWindow
    MainWindow().start()


@cli.command("update-database")
@click.option("--force", is_flag=True, default=False,
              help="Re-download raw ChEMBL data even if already cached.")
def update_database(force):
    """Rebuild molecule_database.json from ChEMBL data.

    By default, raw ChEMBL files are downloaded only if not already cached.
    Use --force to re-download everything from scratch.
    """
    from chemcards.database.services.chembl import download_raw_data, build_molecule_database
    download_raw_data(force=force)
    build_molecule_database()


@cli.command("generate-catalog")
@click.option("--no-functional-groups", is_flag=True, default=False,
              help="Exclude functional groups from the catalog.")
@click.option("--no-fda-approved", is_flag=True, default=False,
              help="Exclude FDA-approved drugs from the catalog.")
@click.option("--separate", is_flag=True, default=False,
              help="Generate a separate PDF for each section.")
@click.option("--out-pdf", default=None,
              help="Output PDF path (ignored if --separate).")
@click.option("--out-dir", default=None,
              help="Output directory for separate PDFs.")
def generate_catalog(no_functional_groups, no_fda_approved, separate, out_pdf, out_dir):
    """Generate a molecule catalog PDF using RDKit."""
    from chemcards.scripts.generate_catalog import generate_catalog, generate_catalog_sections
    include_fg = not no_functional_groups
    include_fda = not no_fda_approved
    try:
        if separate:
            results = generate_catalog_sections(
                out_dir=out_dir, functional_groups=include_fg, fda_approved=include_fda
            )
            if results:
                click.echo(f"Generated {len(results)} PDFs:")
                for r in results:
                    click.echo(f"  - {r}")
            else:
                click.echo("No catalogs generated.")
        else:
            result = generate_catalog(
                out_pdf=out_pdf, functional_groups=include_fg, fda_approved=include_fda
            )
            click.echo(f"Catalog written to: {result}" if result else "No catalog generated.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
