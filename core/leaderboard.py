"""Leaderboard online global via Supabase (REST).

Usa apenas a stdlib (`urllib`). Toda chamada de rede é defensiva: qualquer
falha vira log em PT-BR + retorno neutro, NUNCA derruba o jogo. As credenciais
abaixo são a chave pública `anon` (somente leitura/inserção, conforme as
policies já configuradas no Supabase).
"""

import json
import logging
import time
import urllib.request

logger = logging.getLogger(__name__)

SUPABASE_URL = "https://kooausbgcmhmijgqjcpd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtvb2F1c2JnY21obWlqZ3FqY3BkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIyNDYxNDYsImV4cCI6MjA5NzgyMjE0Nn0.k_7Dd06RqzqCXicuZ-Ft0vMmvW-V6M_YFYuIYs19uss"
TABELA = "leaderboard"
MAX_ENTRIES = 10


def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _request(method: str, endpoint: str, body: dict | None = None):
    """Requisição REST ao Supabase; retorna o JSON ou None (com aviso) em falha."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            corpo = resp.read().decode()
            return json.loads(corpo) if corpo else []
    except Exception as e:  # noqa: BLE001 — rede nunca pode crashar o jogo
        logger.warning("[Leaderboard] Sem conexão: %s", e)
        return None


def buscar_top10() -> list[dict]:
    """Top 10 por menor tempo (ordem crescente). Lista vazia em falha."""
    endpoint = f"{TABELA}?select=nome,tempo,data&order=tempo.asc&limit={MAX_ENTRIES}"
    resultado = _request("GET", endpoint)
    return resultado if resultado else []


def registrar_vitoria(nome: str, tempo_segundos: float) -> int | None:
    """Insere a vitória e retorna a posição (1-based) no top 10, ou None.

    None significa: fora do top 10 OU falha de rede (não distingue, de
    propósito — a UI trata ambos como 'registrado, mas sem destaque').
    """
    entrada = {
        "nome": nome[:16].strip() or "Anônimo",
        "tempo": round(tempo_segundos, 1),
        "data": time.strftime("%d/%m/%Y"),
    }
    _request("POST", TABELA, entrada)
    top = buscar_top10()
    for i, e in enumerate(top):
        if e["nome"] == entrada["nome"] and abs(e["tempo"] - tempo_segundos) < 1.0:
            return i + 1
    return None


def formatar_tempo(segundos: float) -> str:
    """Formata segundos como MM:SS.d (décimos)."""
    m = int(segundos) // 60
    s = int(segundos) % 60
    d = int((segundos - int(segundos)) * 10)
    return f"{m:02d}:{s:02d}.{d}"
