from chemcards.flashcards.core import FilterBase
from chemcards.database.core import MoleculeDB


class MissingTargetFilter(FilterBase):
    def apply(self, molecule_db: "MoleculeDB") -> "MoleculeDB":
        return molecule_db.subset([mol for mol in molecule_db.molecules if mol.target != "unknown"])


FILTERS = [MissingTargetFilter()]
