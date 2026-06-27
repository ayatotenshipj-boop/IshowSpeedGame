"""Preferências locais do jogador, persistidas em JSON.

Arquivo: ~/.config/speedvslabubu/config.json  (Linux/macOS)
         ~/AppData/Roaming/speedvslabubu/config.json  (Windows)

Toda falha de I/O é tolerada — jogo usa defaults. Leitura é cacheada em
memória (_cache) e invalidada a cada set(); sem disco no draw().
"""

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULTS: dict = {
    "dialogo_habilitado": True,
    "volume": 0.7,
}

_cache: dict | None = None


def _get_path() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "speedvslabubu"
    else:
        base = Path.home() / ".config" / "speedvslabubu"
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"


def _ler_disco() -> dict:
    try:
        path = _get_path()
        if not path.exists():
            return dict(DEFAULTS)
        dados = json.loads(path.read_text(encoding="utf-8"))
        return {k: dados.get(k, v) for k, v in DEFAULTS.items()}
    except Exception as e:  # noqa: BLE001
        logger.warning("[Preferências] Não foi possível carregar: %s", e)
        return dict(DEFAULTS)


def carregar() -> dict:
    """Retorna preferências (cacheadas em memória após primeira leitura)."""
    global _cache
    if _cache is None:
        _cache = _ler_disco()
    return _cache


def salvar(dados: dict) -> None:
    """Persiste chaves em config.json e invalida o cache."""
    global _cache
    atual = _ler_disco()
    atual.update(dados)
    try:
        _get_path().write_text(
            json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[Preferências] Não foi possível salvar: %s", e)
    _cache = atual


def get(chave: str):
    """Retorna o valor de uma preferência (ou default)."""
    return carregar().get(chave, DEFAULTS.get(chave))


def set(chave: str, valor) -> None:  # noqa: A001
    """Salva uma preferência e atualiza o cache."""
    salvar({chave: valor})
