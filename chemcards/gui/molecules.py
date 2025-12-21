from chemcards.database.resources import TEMP_DIR
from chemcards.database.core import MoleculeEntry
from chemcards.database.cheminformatics import FunctionalGroup, AnnotatedMoleculeEntry
from chemcards.gui.core import WindowOptions
from chemcards.database.services.chembl import open_chembl_molecule_link
from pydantic import BaseModel
from pathlib import Path
import tempfile
from rdkit.Chem import Draw
from PIL import ImageTk, Image
import tkinter as tk
from functools import partial
import ttkbootstrap as tb

HIGHLIGHT_COLORS = [
    (r / 256, g / 256, b / 256) for r, g, b in [(68, 178, 212), (39, 136, 169)]
]


class MoleculeViz:
    def __init__(self, molecule: MoleculeEntry):
        self.molecule = molecule

    @property
    def img_path(self) -> Path:
        return TEMP_DIR / f"{self.molecule.name}.png"

    def get_image(
        self,
        height=400,
        width=400,
        highlight_functional_groups=False,
        highlight_functional_group: FunctionalGroup = None,
        use_tkinter=True,
    ) -> ImageTk.PhotoImage:

        # if not self.img_path.exists():
        self.img_path.parent.mkdir(exist_ok=True)
        mol = self.molecule.to_rdkit()

        if highlight_functional_groups:
            raise NotImplementedError

        if highlight_functional_group:
            if highlight_functional_group.match(self.molecule):
                # Set Draw Options
                dopts = Draw.rdMolDraw2D.MolDrawOptions()
                dopts.setHighlightColour(HIGHLIGHT_COLORS[0])
                dopts.highlightBondWidthMultiplier = 16

                # Find the atoms to highlight
                highlight = [
                    mol.GetSubstructMatch(highlight_functional_group.to_rdkit())
                ]

                # Draw the molecules
                img = Draw.MolsToGridImage(
                    [mol],
                    subImgSize=(800, 800),
                    molsPerRow=1,
                    highlightAtomLists=highlight,
                    drawOptions=dopts,
                )
                with open(self.img_path, "wb") as f:
                    f.write(img.data)
        else:
            img = Draw.MolToImage(mol, size=(800, 800))
            img.save(self.img_path)

        img = Image.open(self.img_path)
        img = img.resize((height, width))

        if not use_tkinter:
            return img
        else:
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
        self.image_frame.grid(row=0, pady=WindowOptions.edge, padx=WindowOptions.edge)

        self.text_frame = tb.Frame(self.gui)
        self.text_frame.grid(
            row=1, column=0, pady=WindowOptions.between, padx=WindowOptions.edge
        )

        # Add Mol Image
        mviz = MoleculeViz(molecule=molecule)
        img = mviz.get_image()

        image_label = tb.Label(self.image_frame)
        image_label.pack()
        image_label.image = img
        image_label.configure(image=img)

        # Try to accommodate the width of the text without it being too long
        width = max([len(value) for value in molecule.model_dump().values()]) + 2
        width = min(width, 100)

        # Add Text
        i = 0
        for key, value in molecule.model_dump().items():
            if isinstance(value, str):
                label = tb.Label(self.text_frame, text=key, bootstyle="info")
                label.grid(row=i, column=0)
                text = tb.Entry(self.text_frame, width=width)
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
