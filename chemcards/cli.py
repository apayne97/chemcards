from chemcards.gui.mainwindow import MainWindow
import click

# Define the main command group
@click.group("chemcards")
def cli():
    """The CLI for ChemCards."""
    pass

@cli.command("start")
def start():
    main_window = MainWindow()
    main_window.start()

@cli.command("download-database")
def download_database():
    from chemcards.database.services.chembl import main as chembl_main
    chembl_main()

@cli.command("generate-catalog")
@click.option("--no-functional-groups", "functional_groups", is_flag=True, default=False, help="Exclude functional groups.")
@click.option("--no-fda-approved", "fda_approved", is_flag=True, default=False, help="Exclude FDA-approved drugs.")
@click.option("--separate", is_flag=True, default=False, help="Generate separate PDFs for each section.")
@click.option("--out-pdf", "out_pdf", default=None, help="Output PDF path (ignored if --separate).")
@click.option("--out-dir", "out_dir", default=None, help="Output directory (only for --separate).")
def generate_catalog_cmd(functional_groups, fda_approved, separate, out_pdf, out_dir):
    """Generate molecule catalog PDF using RDKit's MolsToGridImage."""
    from chemcards.scripts.generate_catalog import generate_catalog, generate_catalog_sections
    fg = not functional_groups
    fda = not fda_approved
    try:
        if separate:
            results = generate_catalog_sections(out_dir=out_dir, functional_groups=fg, fda_approved=fda)
            if results:
                click.echo(f"Generated {len(results)} PDFs:")
                for r in results:
                    click.echo(f"  - {r}")
            else:
                click.echo("No catalogs generated.")
        else:
            result = generate_catalog(out_pdf=out_pdf, functional_groups=fg, fda_approved=fda)
            if result:
                click.echo(f"Catalog written to: {result}")
            else:
                click.echo("No catalog generated.")
    except Exception as e:
        click.echo(f"Error generating catalog: {e}")
