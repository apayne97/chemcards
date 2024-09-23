from pydantic import BaseModel
from enum import Enum
from chemcards.database.core import MoleculeDB
from abc import abstractmethod


class FlashcardType(Enum):
    pass


class FlashCardBase(BaseModel):
    pass


class FilterBase:

    @abstractmethod
    def apply(self, molecule_db: MoleculeDB) -> MoleculeDB:
        pass

    def __call__(self, molecule_db: MoleculeDB) -> MoleculeDB:
        return self.apply(molecule_db)


class FlashCardGeneratorBase:

    def __init__(self, molecule_db: MoleculeDB, filters: list[FilterBase] = ()):
        self.molecule_db = self.apply_filters(molecule_db, filters)
        self.filters = filters

    @classmethod
    def apply_filters(
        cls, molecule_db: MoleculeDB, filters: list[FilterBase] = ()
    ) -> MoleculeDB:
        for filter in filters:
            molecule_db = filter(molecule_db)
        return molecule_db

    @abstractmethod
    def next(self) -> FlashCardBase:
        pass

    def __iter__(self):
        return self.next()
