"""Sistema de conquistas (Bloco 6, v1.2.1).

Persiste o estado das conquistas num JSON na pasta de config do usuário
(offline-first: qualquer falha de I/O é tolerada e nunca derruba o jogo). Há
uma conquista de vitória por modo de dificuldade.
"""

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Definição das conquistas (estáticas). `desbloqueada` aqui é só o default; o
# estado real vem do JSON persistido.
CONQUISTAS_DEF: dict[str, dict] = {
    "vitoria_facil": {
        "nome": "Treino Completo",
        "descricao": "Zerou o jogo no modo Fácil",
        "icone": "🥉",
    },
    "vitoria_normal": {
        "nome": "Campeão de Miami",
        "descricao": "Zerou o jogo no modo Normal",
        "icone": "🏆",
    },
    "vitoria_dificil": {
        "nome": "Lenda do Speed",
        "descricao": "Zerou o jogo no modo Difícil",
        "icone": "💀",
    },
    "vitoria_hard_2x": {
        "nome": "Sem Piedade",
        "descricao": "Zerou no Difícil com velocidade 2x ativada",
        "icone": "⚡",
    },
    # Categoria: Modo Infinito (alinhadas com boss waves a cada 15)
    "inf_wave_15": {
        "nome": "Só começando",
        "descricao": "Sobreviveu até a wave 15 no Modo Infinito",
        "icone": "🌀",
    },
    "inf_wave_30": {
        "nome": "Pegando o ritmo",
        "descricao": "Sobreviveu até a wave 30 no Modo Infinito",
        "icone": "🌀",
    },
    "inf_wave_45": {
        "nome": "Sem parar",
        "descricao": "Sobreviveu até a wave 45 no Modo Infinito",
        "icone": "🌀",
    },
    "inf_wave_60": {
        "nome": "Isso é sério",
        "descricao": "Sobreviveu até a wave 60 no Modo Infinito",
        "icone": "🌀",
    },
    "inf_wave_75": {
        "nome": "Lendário",
        "descricao": "Sobreviveu até a wave 75 no Modo Infinito",
        "icone": "🏆",
    },
    "vitoria_impossivel": {
        "nome": "Impossível? Feito.",
        "descricao": "Derrotou 100 Ancelottis no Modo Impossível",
        "icone": "💀",
    },
    # IDs legados — mantidos para jogadores que já desbloquearam (não disparados mais)
    "inf_wave_10": {
        "nome": "Só começando (legado)",
        "descricao": "Sobreviveu até a wave 10 no Modo Infinito",
        "icone": "🌀",
    },
    "inf_wave_20": {
        "nome": "Pegando o ritmo (legado)",
        "descricao": "Sobreviveu até a wave 20 no Modo Infinito",
        "icone": "🌀",
    },
    "inf_wave_40": {
        "nome": "Isso é sério (legado)",
        "descricao": "Sobreviveu até a wave 40 no Modo Infinito",
        "icone": "🌀",
    },
    "inf_wave_50": {
        "nome": "Lendário (legado)",
        "descricao": "Sobreviveu até a wave 50 no Modo Infinito",
        "icone": "🏆",
    },
}


def _get_path() -> Path:
    """Caminho do arquivo de conquistas na pasta de config do SO."""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "speedvslabubu"
    else:
        base = Path.home() / ".config" / "speedvslabubu"
    base.mkdir(parents=True, exist_ok=True)
    return base / "conquistas.json"


def carregar() -> dict:
    """Lê o estado persistido. Em qualquer erro, devolve tudo bloqueado."""
    try:
        path = _get_path()
        if not path.exists():
            return {k: False for k in CONQUISTAS_DEF}
        dados = json.loads(path.read_text(encoding="utf-8"))
        # Garante todas as chaves conhecidas (tolera JSON antigo/incompleto).
        return {k: bool(dados.get(k, False)) for k in CONQUISTAS_DEF}
    except Exception as e:  # noqa: BLE001 — offline-first: nunca propaga
        logger.warning("Não foi possível carregar conquistas: %s", e)
        return {k: False for k in CONQUISTAS_DEF}


def salvar(estado: dict) -> None:
    """Grava o estado. Falha de I/O é apenas logada (nunca derruba o jogo)."""
    try:
        _get_path().write_text(
            json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Não foi possível salvar conquistas: %s", e)


def desbloquear(conquista_id: str) -> bool:
    """Desbloqueia `conquista_id`. Retorna True só se foi novidade agora."""
    if conquista_id not in CONQUISTAS_DEF:
        return False
    estado = carregar()
    if estado.get(conquista_id):
        return False
    estado[conquista_id] = True
    salvar(estado)
    return True


def get_todas() -> list[dict]:
    """Lista as conquistas com a definição + flag `desbloqueada` atual."""
    estado = carregar()
    return [
        {**cdef, "id": cid, "desbloqueada": estado.get(cid, False)}
        for cid, cdef in CONQUISTAS_DEF.items()
    ]
