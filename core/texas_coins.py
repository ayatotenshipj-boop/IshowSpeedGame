"""Sistema de TexasCoin: moeda e gacha da loja.

Persiste saldo e itens obtidos em JSON na pasta de config do usuário.
Toda falha de I/O é tolerada (offline-first — nunca derruba o jogo).
"""

import json
import logging
import random
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

PRECO_1X: int = 10
PRECO_10X: int = 100
CHANCE_GANHAR: float = 0.002   # 0.2% por roll
SALDO_INICIAL: int = 10
PLACEHOLDER_ITEM: str = "speed_placeholder"

# Coins ganhos ao VENCER uma fase (chave = modo_dificuldade ou "dificil_2x").
GANHO_POR_MODO: dict[str, int] = {
    "facil":      1,
    "normal":     5,
    "dificil":   15,
    "dificil_2x": 25,
}


def _get_path() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "speedvslabubu"
    else:
        base = Path.home() / ".config" / "speedvslabubu"
    base.mkdir(parents=True, exist_ok=True)
    return base / "texas_coins.json"


def _carregar() -> dict:
    try:
        path = _get_path()
        if not path.exists():
            return {"saldo": SALDO_INICIAL, "itens": []}
        dados = json.loads(path.read_text(encoding="utf-8"))
        return {
            "saldo": int(dados.get("saldo", SALDO_INICIAL)),
            "itens": list(dados.get("itens", [])),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("Não foi possível carregar texas_coins: %s", e)
        return {"saldo": SALDO_INICIAL, "itens": []}


def _salvar(dados: dict) -> None:
    try:
        _get_path().write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Não foi possível salvar texas_coins: %s", e)


def get_saldo() -> int:
    return _carregar()["saldo"]


def get_itens() -> list[str]:
    return _carregar()["itens"]


def adicionar(quantidade: int) -> int:
    """Adiciona `quantidade` ao saldo. Retorna novo saldo."""
    if quantidade <= 0:
        return get_saldo()
    dados = _carregar()
    dados["saldo"] += quantidade
    _salvar(dados)
    logger.info("TexasCoin: +%d  (saldo=%d)", quantidade, dados["saldo"])
    return dados["saldo"]


def remover(quantidade: int) -> int:
    """Remove `quantidade` do saldo (mínimo 0). Retorna novo saldo."""
    if quantidade <= 0:
        return get_saldo()
    dados = _carregar()
    dados["saldo"] = max(0, dados["saldo"] - quantidade)
    _salvar(dados)
    logger.info("TexasCoin: -%d  (saldo=%d)", quantidade, dados["saldo"])
    return dados["saldo"]


def admin_set_saldo(quantidade: int) -> int:
    """Define o saldo diretamente (uso administrativo). Retorna novo saldo."""
    dados = _carregar()
    dados["saldo"] = max(0, int(quantidade))
    _salvar(dados)
    logger.info("TexasCoin [admin]: saldo=%d", dados["saldo"])
    return dados["saldo"]


def admin_adicionar_item(item: str) -> bool:
    """Adiciona item ao inventário sem custo (uso administrativo)."""
    dados = _carregar()
    if item not in dados["itens"]:
        dados["itens"].append(item)
    _salvar(dados)
    return True


def admin_remover_item(item: str) -> bool:
    """Remove item do inventário (uso administrativo). Retorna False se ausente."""
    dados = _carregar()
    if item in dados["itens"]:
        dados["itens"].remove(item)
        _salvar(dados)
        return True
    return False


def rolar(n: int = 1) -> dict:
    """Realiza `n` rolls do gacha.

    Retorna:
      - {"erro": "saldo_insuficiente", "saldo": int}  — se coins insuficientes
      - {"gasto": int, "ganhos": list[str], "saldo": int}  — caso contrário

    Itens já possuídos não duplicam no inventário (registrado apenas uma vez).
    """
    custo = PRECO_1X * n
    dados = _carregar()
    if dados["saldo"] < custo:
        return {"erro": "saldo_insuficiente", "saldo": dados["saldo"]}

    dados["saldo"] -= custo
    ganhos: list[str] = []
    for _ in range(n):
        if random.random() < CHANCE_GANHAR:
            item = PLACEHOLDER_ITEM
            ganhos.append(item)
            if item not in dados["itens"]:
                dados["itens"].append(item)

    _salvar(dados)
    return {"gasto": custo, "ganhos": ganhos, "saldo": dados["saldo"]}
