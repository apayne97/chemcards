from chemcards.database.resources import TEMP_DIR
from chemcards.database.core import MoleculeEntry
from chemcards.gui.core import PaddingAndSize
from chemcards.database.services.chembl import open_chembl_molecule_link
from pydantic import BaseModel
from pathlib import Path
import tempfile
from rdkit.Chem import Draw
from PIL import ImageTk, Image
import tkinter as tk
from functools import partial
import ttkbootstrap as tb


class MoleculeViz:
    def __init__(self, molecule: MoleculeEntry):
        self.molecule = molecule

    @property
    def img_path(self) -> Path:
        return TEMP_DIR / f"{self.molecule.name}.png"

    def get_image(self) -> Path:

        # if not self.img_path.exists():
        self.img_path.parent.mkdir(exist_ok=True)
        mol = self.molecule.to_rdkit()
        img = Draw.MolToImage(mol, size=(800, 800))
        img.save(self.img_path)

        img = Image.open(self.img_path)
        img = img.resize((400, 400))
        img = ImageTk.PhotoImage(img)

        return img


class MoleculeWindow:

    def __init__(self, molecule: MoleculeEntry, gui: tb.Window = None):
        if gui is None:
            self.gui = tb.Window(themename="superhero")
        else:
            self.gui = tb.Toplevel(gui)
        self.gui.title(molecule.name)

        self.image_frame = tb.Frame(self.gui)
        self.image_frame.grid(row=0, pady=PaddingAndSize.edge, padx=PaddingAndSize.edge)

        self.text_frame = tb.Frame(self.gui)
        self.text_frame.grid(
            row=1, column=0, pady=PaddingAndSize.between, padx=PaddingAndSize.edge
        )

        # Add Mol Image
        mviz = MoleculeViz(molecule=molecule)
        img = mviz.get_image()

        image_label = tb.Label(self.image_frame)
        image_label.pack()
        image_label.image = img
        image_label.configure(image=img)

        # Add Text
        i = 0
        for key, value in molecule.model_dump().items():
            if isinstance(value, str):
                label = tb.Label(self.text_frame, text=key, bootstyle="info")
                label.grid(row=i, column=0)
                text = tb.Entry(self.text_frame, width=len(value))
                text.insert(0, value)
                text.grid(row=i, column=1)

                i += 1

        # Add Chembl Link
        partial_func = partial(open_chembl_molecule_link, molecule)
        chembl_button = tb.Button(
            self.text_frame,
            text="Open Chembl Molecule Link",
            bootstyle="info",
            command=partial_func,
        )
        chembl_button.grid(row=i, column=1)

        self.gui.mainloop()
