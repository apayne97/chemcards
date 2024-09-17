from pydantic import BaseModel, Field
from chemcards.database.resources import DATABASE
import json

class MoleculeEntry(BaseModel):
    name: str
    target: str
    indication: str