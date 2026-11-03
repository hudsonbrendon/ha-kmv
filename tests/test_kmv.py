"""Testes unitários leves do KMV (sem HA rodando)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_COORD = Path(__file__).resolve().parent.parent / "custom_components" / "kmv" / "coordinator.py"


def _load_find_points_balance():
    """Carrega só a função pura, sem importar o pacote HA inteiro."""
    source = _COORD.read_text()
    start = source.index("def find_points_balance")
    end = source.index("\nclass ")
    namespace: dict = {"Any": object}
    exec(compile(source[start:end], str(_COORD), "exec"), namespace)  # noqa: S102
    return namespace["find_points_balance"]


find_points_balance = _load_find_points_balance()


def test_find_points_balance_nested() -> None:
    """Acha kmvPoints enterrado numa árvore SDUI."""
    tree = {
        "data": {
            "components": [
                {"type": "navbar"},
                {"type": "card", "props": {"kmvPoints": 12345, "tierLabel": "Ouro"}},
            ]
        }
    }
    assert find_points_balance(tree) == 12345


def test_find_points_balance_in_list() -> None:
    """Varre listas também."""
    assert find_points_balance([{"a": 1}, {"userBalance": 42}]) == 42


def test_find_points_balance_missing() -> None:
    """Sem campo conhecido -> None (não quebra)."""
    assert find_points_balance({"foo": {"bar": "baz"}}) is None
    assert find_points_balance({"kmvPoints": "não-número"}) is None


if __name__ == "__main__":
    test_find_points_balance_nested()
    test_find_points_balance_in_list()
    test_find_points_balance_missing()
    print("all tests passed")
