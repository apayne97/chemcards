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