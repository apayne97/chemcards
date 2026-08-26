"""Tests for functional group data consistency and catalog sort order."""
import yaml
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "chemcards" / "database" / "data"
FG_YAML = DATA_DIR / "functional_groups.yaml"
CATEGORIES_YAML = DATA_DIR / "functional_group_categories.yaml"


def _load_yaml(path: Path):
    with path.open("r", encoding="utf8") as fh:
        return yaml.safe_load(fh) or []


def _normalise(category: str) -> str:
    """Normalise category to canonical form used in the categories list."""
    return category.replace("_", " ").strip().lower()


@pytest.fixture(scope="module")
def functional_groups():
    return _load_yaml(FG_YAML)


@pytest.fixture(scope="module")
def canonical_categories():
    return [str(c).strip().lower() for c in _load_yaml(CATEGORIES_YAML)]


class TestFunctionalGroupCategories:
    def test_all_groups_have_a_category(self, functional_groups):
        missing = [fg["name"] for fg in functional_groups if not fg.get("category")]
        assert missing == [], f"Functional groups missing 'category': {missing}"

    def test_all_categories_in_canonical_list(self, functional_groups, canonical_categories):
        unknown = {
            _normalise(fg["category"])
            for fg in functional_groups
            if _normalise(fg.get("category", "")) not in canonical_categories
        }
        assert unknown == set(), (
            f"Functional group categories not in functional_group_categories.yaml: {unknown}"
        )

    def test_catalog_sort_order_matches_canonical_category_order(
        self, functional_groups, canonical_categories
    ):
        from chemcards.scripts.generate_catalog import _load_functional_groups, _load_category_order

        sorted_groups = _load_functional_groups(FG_YAML)
        category_rank = {c: i for i, c in enumerate(canonical_categories)}

        ranks = [
            category_rank.get(_normalise(fg["category"]), len(canonical_categories))
            for fg in sorted_groups
        ]
        assert ranks == sorted(ranks), (
            "Functional groups in catalog are not sorted by canonical category order.\n"
            f"Category sequence: {[fg['category'] for fg in sorted_groups]}"
        )


HETEROCYCLE_CATEGORIES = {
    "nitrogen_heterocycles",
    "oxygen_heterocycles",
    "sulfur_heterocycles",
    "multiple_heteroatom_heterocycles",
}


class TestFunctionalGroupVsChemicalBuildingBlockSplit:
    def test_all_groups_have_a_kind(self, functional_groups):
        missing = [fg["name"] for fg in functional_groups if not fg.get("kind")]
        assert missing == [], f"Functional groups missing 'kind': {missing}"

    def test_heterocycle_categories_are_chemical_building_blocks(self, functional_groups):
        mismatched = [
            fg["name"] for fg in functional_groups
            if fg.get("category") in HETEROCYCLE_CATEGORIES
            and fg.get("kind") != "chemical_building_block"
        ]
        assert mismatched == [], (
            f"Heterocycle-category entries not tagged kind=chemical_building_block: {mismatched}"
        )

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

