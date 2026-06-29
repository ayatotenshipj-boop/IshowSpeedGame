"""Sistema de TexasCoin: moeda e gacha da loja.

Persiste saldo e itens obtidos em JSON na pasta de config do usuário.
Toda falha de I/O é tolerada (offline-first — nunca derruba o jogo).
"""

import json
import logging
import random
import sys
from pathlib import Path

# Caminho do arquivo de códigos promo (relativo à raiz do projeto).
# Deve estar no .gitignore — nunca commitar com códigos reais.
_CODIGOS_PATH: Path = Path(__file__).resolve().parent.parent / "config" / "codigos_promo.json"

logger = logging.getLogger(__name__)

PRECO_1X: int = 10
PRECO_10X: int = 100
CHANCE_GANHAR: float = 0.002   # 0.2% por roll
SALDO_INICIAL: int = 10
PLACEHOLDER_ITEM: str = "speed_placeholder"
ITEM_DRIVING_CAR_SPEED: str = "driving_car_speed"
PITY_LIMITE: int = 120
# DrivingCarSpeed é carta limitada: jogador só pode ter 1 cópia.
# Aplicado em rolar() e admin_adicionar_item() via `if item not in dados["itens"]`.
MAX_COPIAS_DCS: int = 1

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
            return {"saldo": SALDO_INICIAL, "itens": [], "pity_counter": 0, "deck": [], "codigos_usados": []}
        dados = json.loads(path.read_text(encoding="utf-8"))
        return {
            "saldo": int(dados.get("saldo", SALDO_INICIAL)),
            "itens": list(dados.get("itens", [])),
            "pity_counter": int(dados.get("pity_counter", 0)),
            "deck": list(dados.get("deck", [])),
            "codigos_usados": list(dados.get("codigos_usados", [])),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("Não foi possível carregar texas_coins: %s", e)
        return {"saldo": SALDO_INICIAL, "itens": [], "pity_counter": 0, "deck": [], "codigos_usados": []}


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


def get_deck() -> list[str]:
    """Retorna o deck ativo (lista de asset_names das torres equipadas)."""
    dados = _carregar()
    return list(dados.get("deck", []))


def salvar_deck(deck: list[str]) -> None:
    """Persiste o deck ativo."""
    dados = _carregar()
    dados["deck"] = list(deck)
    _salvar(dados)


def get_pity_counter() -> int:
    """Retorna o contador de pity atual."""
    return _carregar().get("pity_counter", 0)


def rolar(n: int = 1) -> dict:
    """Realiza `n` rolls do gacha com sistema de pity.

    Retorna:
      - {"erro": "saldo_insuficiente", "saldo": int}
      - {"gasto": int, "ganhos": list[str], "saldo": int, "pity_counter": int}

    Pity: ao atingir PITY_LIMITE pulls sem obter DrivingCarSpeed, o próximo
    pull garante a carta. Contador reseta ao obtê-la.
    """
    custo = PRECO_1X * n
    dados = _carregar()
    if dados["saldo"] < custo:
        return {"erro": "saldo_insuficiente", "saldo": dados["saldo"]}

    dados["saldo"] -= custo
    ganhos: list[str] = []

    for _ in range(n):
        dados["pity_counter"] += 1
        pity_garantido = dados["pity_counter"] >= PITY_LIMITE
        logger.info("[Pity] Contador atual: %d/%d", dados["pity_counter"], PITY_LIMITE)
        item = None

        if pity_garantido or random.random() < CHANCE_GANHAR:
            item = ITEM_DRIVING_CAR_SPEED
        elif random.random() < CHANCE_GANHAR:
            item = PLACEHOLDER_ITEM

        if item is not None:
            ja_possui = item in dados["itens"]
            if not ja_possui:
                dados["itens"].append(item)
                ganhos.append(item)
            elif item == ITEM_DRIVING_CAR_SPEED:
                # Pity disparou mas jogador já possui DrivingCarSpeed (limite=1 cópia).
                # Não duplica no inventário; não lista nos ganhos.
                logger.info("[Pity] DrivingCarSpeed já obtida — pity consumido sem duplicar.")
            if item == ITEM_DRIVING_CAR_SPEED:
                dados["pity_counter"] = 0

    _salvar(dados)
    return {
        "gasto": custo,
        "ganhos": ganhos,
        "saldo": dados["saldo"],
        "pity_counter": dados["pity_counter"],
    }


def resgatar_codigo(codigo: str) -> dict:
    """Resgata código promo e credita TexasCoin.

    Retorna:
      {"ok": True, "tc": int, "saldo": int}   — sucesso
      {"erro": "nao_encontrado"}               — código inválido
      {"erro": "ja_usado"}                     — já resgatado nesta instalação
      {"erro": "arquivo_ausente"}              — codigos_promo.json não existe
    """
    codigo = codigo.strip().upper()
    if not codigo:
        return {"erro": "nao_encontrado"}

    if not _CODIGOS_PATH.exists():
        logger.warning("Arquivo de códigos promo não encontrado: %s", _CODIGOS_PATH)
        return {"erro": "arquivo_ausente"}

    try:
        codigos: dict = json.loads(_CODIGOS_PATH.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning("Erro ao ler codigos_promo.json: %s", e)
        return {"erro": "arquivo_ausente"}

    if codigo not in codigos:
        return {"erro": "nao_encontrado"}

    dados = _carregar()
    if codigo in dados["codigos_usados"]:
        return {"erro": "ja_usado"}

    tc = int(codigos[codigo])
    dados["saldo"] += tc
    dados["codigos_usados"].append(codigo)
    _salvar(dados)
    logger.info("Código '%s' resgatado: +%d TC (saldo=%d)", codigo, tc, dados["saldo"])
    return {"ok": True, "tc": tc, "saldo": dados["saldo"]}
