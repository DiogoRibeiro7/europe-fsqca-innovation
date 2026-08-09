from __future__ import annotations

from pathlib import Path

import pandas as pd

from euro_fsqca.data.regions import attach_regions, load_region_map


def test_macro3_maps_all_eu27() -> None:
    root = Path(__file__).resolve().parents[1]
    mapping = load_region_map(root / "configs" / "regions.yml", "macro3")
    assert len(mapping) == 27
    assert mapping["Portugal"] == "south"
    assert mapping["Germany"] == "north_west"
    assert mapping["Poland"] == "central_east"


def test_attach_regions_fails_for_unknown_country() -> None:
    frame = pd.DataFrame({"country": ["Portugal", "Atlantis"]})
    mapping = {"Portugal": "south"}
    try:
        attach_regions(frame, country_column="country", mapping=mapping)
    except ValueError as exc:
        assert "Atlantis" in str(exc)
    else:
        raise AssertionError("expected unknown country to fail")
