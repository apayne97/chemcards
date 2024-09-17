from chemcards.database.resources import TEMP_DIR
from chemcards.database.core import MoleculeEntry
from pydantic import BaseModel
from pathlib import Path
import tempfile
from rdkit.Chem import Draw

class MoleculeViz():
    def __init__(self, molecule: MoleculeEntry):
        self.molecule = molecule

    @property
    def img_path(self) -> Path:
        return TEMP_DIR / f"{self.molecule.name}.png"

    def get_image(self) -> Path:
        if self.img_path.exists():
            return self.img_path
        else:
            self.img_path.parent.mkdir(exist_ok=True)
            mol = self.molecule.to_rdkit()
            img = Draw.MolToImage(mol, size=(800,800))
            img.save(self.img_path)
        return self.img_path
            
