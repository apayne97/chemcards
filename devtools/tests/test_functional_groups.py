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

