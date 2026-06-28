"""Perfil local do jogador com integridade HMAC.

Detecta adulteração do JSON via HMAC-SHA256 derivado do player_id + salt.
Valida sessões de partida antes de conceder TexasCoin.

Fluxo:
  1. `iniciar_sessao(modo)` → retorna nonce, salva no perfil assinado.
  2. `finalizar_sessao(nonce, tempo)` → verifica nonce + TTL + HMAC,
     chama texas_coins.adicionar() internamente e atualiza estatísticas.
"""

import hashlib
import hmac as _hmac
import json
import logging
import sys
import time
import uuid
from pathlib import Path

from core import texas_coins

logger = logging.getLogger(__name__)

_SALT = b":speedvslabubu:perfil_v1"
_SESSAO_TTL = 10800.0   # 3 horas — sessões mais longas são rejeitadas


def _get_path() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "speedvslabubu"
    else:
        base = Path.home() / ".config" / "speedvslabubu"
    base.mkdir(parents=True, exist_ok=True)
    return base / "player_profile.json"


def _make_key(player_id: str) -> bytes:
    return hashlib.sha256(player_id.encode() + _SALT).digest()


def _calcular_sig(dados: dict, key: bytes) -> str:
    sem_sig = {k: v for k, v in dados.items() if k != "_sig"}
    payload = json.dumps(sem_sig, sort_keys=True, ensure_ascii=False)
    return _hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def _perfil_novo() -> dict:
    return {
        "player_id": str(uuid.uuid4()),
        "partidas_concluidas": 0,
        "texascoins_ganhos": 0,
        "melhor_tempo": {},
        "sessao_ativa": None,
    }


def _carregar() -> tuple[dict, bytes]:
    """Carrega e verifica perfil. Recria se ausente ou corrompido."""
    path = _get_path()
    try:
        if path.exists():
            dados = json.loads(path.read_text(encoding="utf-8"))
            pid = dados.get("player_id", "")
            if pid:
                key = _make_key(pid)
                sig_salva = dados.get("_sig", "")
                sig_calc = _calcular_sig(dados, key)
                if _hmac.compare_digest(sig_salva, sig_calc):
                    return dados, key
                logger.warning("Perfil corrompido ou adulterado — recriando.")
    except Exception as exc:
        logger.warning("Erro ao ler perfil: %s", exc)

    novo = _perfil_novo()
    key = _make_key(novo["player_id"])
    _salvar(novo, key)
    return novo, key


def _salvar(dados: dict, key: bytes) -> None:
    dados["_sig"] = _calcular_sig(dados, key)
    try:
        _get_path().write_text(
            json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("Erro ao salvar perfil: %s", exc)


# ── API pública ──────────────────────────────────────────────────────────────

def get_player_id() -> str:
    dados, _ = _carregar()
    return dados["player_id"]


def iniciar_sessao(modo: str) -> str:
    """Registra início de partida. Retorna nonce p/ `finalizar_sessao`."""
    dados, key = _carregar()
    nonce = str(uuid.uuid4())
    dados["sessao_ativa"] = {
        "nonce": nonce,
        "timestamp": time.time(),
        "modo": modo,
    }
    _salvar(dados, key)
    logger.info("Sessão iniciada: modo=%s", modo)
    return nonce


def finalizar_sessao(nonce: str | None, tempo: float) -> bool:
    """Valida sessão, concede TexasCoin e atualiza estatísticas.

    Retorna True se aceita. Rejeita se nonce inválido, sessão expirada ou
    perfil adulterado (HMAC falhou → perfil resetado automaticamente).
    """
    if not nonce:
        logger.warning("Sessão sem nonce — coins não concedidos.")
        return False

    dados, key = _carregar()
    sessao = dados.get("sessao_ativa")
    if not sessao:
        logger.warning("Nenhuma sessão ativa no perfil — coins não concedidos.")
        return False

    if not _hmac.compare_digest(sessao.get("nonce", ""), nonce):
        logger.warning("Nonce não confere — coins não concedidos.")
        return False

    age = time.time() - float(sessao.get("timestamp", 0))
    if age > _SESSAO_TTL:
        logger.warning("Sessão expirada (%.0fs > %.0fs).", age, _SESSAO_TTL)
        dados["sessao_ativa"] = None
        _salvar(dados, key)
        return False

    modo = sessao.get("modo", "normal")
    ganho = texas_coins.GANHO_POR_MODO.get(modo, 0)
    if ganho > 0:
        texas_coins.adicionar(ganho)
        dados["texascoins_ganhos"] = dados.get("texascoins_ganhos", 0) + ganho

    dados["partidas_concluidas"] = dados.get("partidas_concluidas", 0) + 1
    melhor = dados.setdefault("melhor_tempo", {})
    if tempo > 0 and (modo not in melhor or tempo < melhor[modo]):
        melhor[modo] = round(tempo, 2)

    dados["sessao_ativa"] = None
    _salvar(dados, key)
    logger.info("Sessão finalizada: modo=%s, tempo=%.1fs, +%d TC", modo, tempo, ganho)
    return True


def get_stats() -> dict:
    """Retorna estatísticas do jogador (somente leitura)."""
    dados, _ = _carregar()
    return {
        "player_id": dados.get("player_id", "?")[:8] + "...",
        "partidas_concluidas": dados.get("partidas_concluidas", 0),
        "texascoins_ganhos": dados.get("texascoins_ganhos", 0),
        "melhor_tempo": dict(dados.get("melhor_tempo", {})),
    }
