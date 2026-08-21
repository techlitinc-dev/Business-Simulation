"""Unit tests for the industry pack registry."""

from __future__ import annotations

# Imports register the packs (module side-effect).
import app.services.industry_packs.ecommerce_pack  # noqa: F401
import app.services.industry_packs.saas_pack  # noqa: F401
from app.services.industry_packs.pack_registry import get_pack, list_packs


def test_saas_pack_registered() -> None:
    pack = get_pack("saas")
    assert pack is not None
    assert pack.name == "SaaS Pack"
    assert len(pack.hurdle_library) == 10


def test_ecommerce_pack_registered() -> None:
    pack = get_pack("ecommerce")
    assert pack is not None
    assert len(pack.hurdle_library) == 10


def test_list_packs_returns_both() -> None:
    packs = list_packs()
    ids = [p["id"] for p in packs]
    assert "saas" in ids
    assert "ecommerce" in ids


def test_saas_blueprint_template_has_required_fields() -> None:
    pack = get_pack("saas")
    assert pack is not None
    assert "starting_capital" in pack.blueprint_template["financials"]
    assert "monthly_price" in pack.blueprint_template["pricing"]


def test_saas_engine_params_have_churn() -> None:
    pack = get_pack("saas")
    assert pack is not None
    assert "monthly_churn" in pack.engine_params
    assert pack.engine_params["monthly_churn"] < 0.10


def test_unknown_pack_returns_none() -> None:
    assert get_pack("restaurant") is None


def test_ecommerce_vertical_kpis() -> None:
    pack = get_pack("ecommerce")
    assert pack is not None
    assert "average_order_value" in pack.vertical_kpis
