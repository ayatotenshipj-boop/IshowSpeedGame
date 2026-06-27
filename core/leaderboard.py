"""Leaderboard online global via Supabase (REST).

Usa apenas a stdlib (`urllib`). Toda chamada de rede é defensiva: qualquer
falha vira log em PT-BR + retorno neutro, NUNCA derruba o jogo. As credenciais
abaixo são a chave pública `anon` (somente leitura/inserção, conforme as
policies já configuradas no Supabase).

Identidade do jogador: cada instalação tem um `player_id` (UUID) persistido em
arquivo local. O registro de vitória é um UPSERT por `player_id` (idempotente),
evitando que reabrir o jogo ou usar nomes diferentes lote o banco. A data
exibida vem do `created_at` (timezone UTC do servidor), convertido para
horário de Brasília — nunca do relógio local do jogador.
"""

import json
import logging
import ssl
import sys
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _ssl_context() -> ssl.SSLContext:
    """Contexto SSL que funciona dentro do exe PyInstaller (sem CA do sistema).

    O bundle do PyInstaller não traz os certificados do SO, então `urllib`
    falha com CERTIFICATE_VERIFY_FAILED. Usa o CA bundle do `certifi` (incluído
    no build); se faltar, cai para um contexto sem verificação — o leaderboard é
    público, somente placar, sem dado sensível.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001 — sem certifi: conexão tolerante
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


_SSL_CTX = _ssl_context()

SUPABASE_URL = "https://kooausbgcmhmijgqjcpd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtvb2F1c2JnY21obWlqZ3FqY3BkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIyNDYxNDYsImV4cCI6MjA5NzgyMjE0Nn0.k_7Dd06RqzqCXicuZ-Ft0vMmvW-V6M_YFYuIYs19uss"
TABELA = "leaderboard"
MAX_ENTRIES = 10

# Cache em memória do player_id (resolvido uma vez por execução).
_PLAYER_ID_CACHE: str | None = None


def _headers(upsert: bool = False) -> dict:
    """Cabeçalhos REST. `upsert=True` ativa o merge por chave de conflito."""
    # Usamos return=minimal no POST para o Supabase não tentar buscar uma 
    # coluna 'id' que não existe, resolvendo o erro 400 original.
    if upsert:
        prefer = "resolution=merge-duplicates,return=minimal"
    else:
        prefer = "return=representation"
        
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _request(method: str, endpoint: str, body: dict | None = None, upsert: bool = False):
    """Requisição REST ao Supabase; retorna o JSON ou None (com aviso) em falha."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(upsert), method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=5, context=_SSL_CTX) as resp:
            corpo = resp.read().decode()
            return json.loads(corpo) if corpo else []
    except urllib.error.HTTPError as e:
        # CAPTURA O CORPO DO ERRO DO SUPABASE
        error_body = e.read().decode('utf-8')
        print("\n" + "="*50)
        print("🚨 ERRO DO SUPABASE DETECTADO 🚨")
        print(f"Código: {e.code}")
        print(f"Mensagem do Banco: {error_body}")
        print("="*50 + "\n")
        logger.warning("[Leaderboard] Sem conexão: %s", e)
        return None
    except Exception as e:  # noqa: BLE001 — rede nunca pode crashar o jogo
        logger.warning("[Leaderboard] Sem conexão: %s", e)
        return None


# --------------------------------------------------------------------------- #
# Identidade do jogador (UUID por instalação)
# --------------------------------------------------------------------------- #
def _get_player_id_path() -> Path:
    """Caminho do arquivo de player_id (por SO). Cria o diretório-pai."""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "speedvslabubu"
    else:
        base = Path.home() / ".config" / "speedvslabubu"
    base.mkdir(parents=True, exist_ok=True)
    return base / "player_id"


def _get_or_create_player_id() -> str:
    """UUID estável da instalação. Cacheado; nunca derruba o jogo.

    Se o arquivo existir, carrega; senão gera e salva. Em FS read-only / sem
    permissão / disco cheio, cai para um UUID efêmero (degradação graciosa: a
    idempotência some nesse caso raro, mas o registro ainda funciona).
    """
    global _PLAYER_ID_CACHE
    if _PLAYER_ID_CACHE:
        return _PLAYER_ID_CACHE
    try:
        path = _get_player_id_path()
        if path.exists():
            pid = path.read_text(encoding="utf-8").strip()
            if pid:
                _PLAYER_ID_CACHE = pid
                return pid
        pid = str(uuid.uuid4())
        path.write_text(pid, encoding="utf-8")
    except Exception:  # noqa: BLE001 — FS indisponível: UUID efêmero, sem crash
        logger.warning("[Leaderboard] Não foi possível persistir player_id; usando efêmero.")
        pid = str(uuid.uuid4())
    _PLAYER_ID_CACHE = pid
    return pid


# --------------------------------------------------------------------------- #
# Datas
# --------------------------------------------------------------------------- #
def _formatar_data_utc(created_at_str: str | None) -> str:
    """Converte o `created_at` UTC do Supabase para horário de Brasília (UTC-3).

    Defensivo: `created_at` ausente ou em formato inesperado retorna string
    vazia — nunca lança (o leaderboard não pode crashar por uma data).
    """
    if not created_at_str:
        return ""
    try:
        dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        dt_br = dt.astimezone(timezone(timedelta(hours=-3)))
        return dt_br.strftime("%d/%m/%Y")
    except Exception:  # noqa: BLE001 — formato inesperado não derruba o jogo
        return ""


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #
def buscar_top10() -> list[dict]:
    """Top 10 por menor tempo (ordem crescente). Lista vazia em falha."""
    endpoint = (
        f"{TABELA}?select=nome,tempo,created_at,player_id"
        f"&order=tempo.asc&limit={MAX_ENTRIES}"
    )
    resultado = _request("GET", endpoint)
    if not resultado:
        return []
    for e in resultado:
        e["data"] = _formatar_data_utc(e.get("created_at"))
    return resultado

def buscar_record_proprio() -> dict | None:
    """Retorna {'nome': ..., 'tempo': ...} do jogador atual ou None."""
    player_id = _get_or_create_player_id()
    resultado = _request("GET", f"{TABELA}?player_id=eq.{player_id}&select=nome,tempo")
    if resultado:
        return resultado[0]
    return None


def registrar_vitoria(nome: str, tempo_segundos: float) -> int | None:
    """Registra a vitória e retorna a posição no top 10.

    O banco tem um trigger que só aceita UPDATE quando o novo tempo é estritamente
    menor que o existente. A função busca o record atual do jogador antes de tentar:
    — Novo record (tempo menor): UPSERT com novo nome + tempo.
    — Primeiro registro: INSERT normal.
    — Tempo não melhorou: retorna a posição atual sem alterar o banco.
    """
    player_id = _get_or_create_player_id()
    nome_sanitizado = nome[:16].strip() or "Anônimo"
    novo_tempo = round(tempo_segundos, 1)

    # Busca entrada existente para comparar tempos.
    existente = _request("GET", f"{TABELA}?player_id=eq.{player_id}&select=tempo")
    if existente:
        tempo_salvo = existente[0].get("tempo", float("inf"))
        if novo_tempo >= tempo_salvo:
            # Não melhorou: apenas retorna posição atual, sem tocar no banco.
            top = buscar_top10()
            for i, e in enumerate(top):
                if e.get("player_id") == player_id:
                    return i + 1
            return None

    entrada = {
        "nome": nome_sanitizado,
        "tempo": novo_tempo,
        "player_id": player_id,
    }
    _request("POST", f"{TABELA}?on_conflict=player_id", entrada, upsert=True)

    top = buscar_top10()
    for i, e in enumerate(top):
        if e.get("player_id") == player_id:
            return i + 1
    return None


def formatar_tempo(segundos: float) -> str:
    """Formata segundos como MM:SS.d (décimos)."""
    m = int(segundos) // 60
    s = int(segundos) % 60
    d = int((segundos - int(segundos)) * 10)
    return f"{m:02d}:{s:02d}.{d}"
