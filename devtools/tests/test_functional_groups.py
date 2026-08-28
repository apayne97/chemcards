"""Tests for functional group data consistency and catalog sort order."""
import yaml
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "chemcards" / "database" / "data"
FG_YAML = DATA_DIR / "functional_groups.yaml"


def _load_yaml(path: Path):
    with path.open("r", encoding="utf8") as fh:
        return yaml.safe_load(fh) or []


@pytest.fixture(scope="module")
def functional_groups():
    return _load_yaml(FG_YAML)


class TestFunctionalGroupTags:
    def test_all_groups_have_tags(self, functional_groups):
        missing = [fg["name"] for fg in functional_groups if not fg.get("tags")]
        assert missing == [], f"Functional groups missing 'tags': {missing}"

    def test_all_tags_in_canonical_list(self, functional_groups):
        from chemcards.database.cheminformatics import CANONICAL_TAGS

        unknown = {
            tag
            for fg in functional_groups
            for tag in fg.get("tags", [])
            if tag not in CANONICAL_TAGS
        }
        assert unknown == set(), (
            f"Tags not in cheminformatics.CANONICAL_TAGS: {unknown}. "
            "If this is a deliberate new tag (e.g. adding amino acids/nucleotides), "
            "add it to CANONICAL_TAGS."
        )

    def test_catalog_sort_order_matches_element_composition_order(self, functional_groups):
        from chemcards.scripts.generate_catalog import (
            _load_functional_groups, _catalog_sort_key, _GROUP_LABELS,
        )

        sorted_groups = _load_functional_groups(FG_YAML)
        by_name = {fg["name"]: fg for fg in functional_groups}

        keys = [_catalog_sort_key(by_name[g["name"]]) for g in sorted_groups]
        assert keys == sorted(keys), (
            "Functional groups in catalog are not sorted by element-composition order "
            "(hydrocarbon, oxygen-only, nitrogen-only, sulfur-only, halogen-only, mixed, heterocycle).\n"
            f"Sequence: {[(g['name'], g['group_label']) for g in sorted_groups]}"
        )
        # Sanity-check group_label matches _catalog_sort_key's own group choice.
        for g in sorted_groups:
            assert g["group_label"] == _GROUP_LABELS[_catalog_sort_key(by_name[g["name"]])[0]]


class TestFunctionalGroupVsChemicalBuildingBlockSplit:
    """`kind` (functional_group vs chemical_building_block) is a content classification, not
    a structural one — "ring" is a plain structural tag now (see CANONICAL_TAGS) and doesn't
    imply kind either way. A handful of functional groups (aryl halide, the quinones, phenyl
    acetamide) have a ring without being chemical building blocks in their own right."""

    def test_all_groups_have_a_kind(self, functional_groups):
        missing = [fg["name"] for fg in functional_groups if not fg.get("kind")]
        assert missing == [], f"Functional groups missing 'kind': {missing}"

    def test_functional_groups_module_split_matches_yaml(self, functional_groups):
        from chemcards.database.cheminformatics import FUNCTIONAL_GROUPS, CHEMICAL_BUILDING_BLOCKS

        yaml_fg_names = {fg["name"] for fg in functional_groups if fg.get("kind") == "functional_group"}
        yaml_cbb_names = {fg["name"] for fg in functional_groups if fg.get("kind") == "chemical_building_block"}

        assert {fg.name for fg in FUNCTIONAL_GROUPS} == yaml_fg_names
        assert {fg.name for fg in CHEMICAL_BUILDING_BLOCKS} == yaml_cbb_names
        assert "urea" in yaml_fg_names

    def test_chemical_building_blocks_are_tagged(self):
        from chemcards.database.cheminformatics import CHEMICAL_BUILDING_BLOCKS

        untagged = [cbb.name for cbb in CHEMICAL_BUILDING_BLOCKS if not cbb.tags]
        assert untagged == [], f"Chemical building blocks missing tags: {untagged}"

    def test_compute_tags_matches_curated_tags(self):
        """compute_tags() derives tags from an arbitrary molecule for the "Draw the
        Structure" quiz mode — it must agree with every hand-curated entry's own tags,
        since the game compares a player's drawn structure against a curated target."""
        from rdkit import Chem
        from chemcards.database.cheminformatics import (
            FUNCTIONAL_GROUPS, CHEMICAL_BUILDING_BLOCKS, compute_tags,
        )

        mismatches = []
        for fg in FUNCTIONAL_GROUPS + CHEMICAL_BUILDING_BLOCKS:
            mol = Chem.MolFromSmiles(fg.display_smiles) if fg.display_smiles else Chem.MolFromSmarts(fg.smarts)
            if compute_tags(mol) != set(fg.tags):
                mismatches.append(fg.name)
        assert mismatches == [], f"compute_tags() disagrees with curated tags for: {mismatches}"
