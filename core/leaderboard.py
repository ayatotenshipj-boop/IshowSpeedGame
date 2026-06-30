"""Leaderboard online global via Supabase (REST).

Usa apenas a stdlib (`urllib`). Toda chamada de rede é defensiva: qualquer
falha vira log em PT-BR + retorno neutro, NUNCA derruba o jogo. Credenciais
lidas de `config/secrets.py` (chave pública `anon` com env-override).

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

from config.secrets import SUPABASE_KEY, SUPABASE_URL

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

TABELA = "leaderboard"
MAX_ENTRIES = 10

# Mapeamento de categorias: chave, label exibida, campo de ordenação e direção.
CATEGORIAS: dict[str, dict] = {
    "normal_speedrun": {"label": "Normal",  "campo": "tempo", "ordem": "asc"},
    "hard_speedrun":   {"label": "Difícil", "campo": "tempo", "ordem": "asc"},
    "infinite_waves":  {"label": "Infinito","campo": "valor", "ordem": "desc"},
}

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
        logger.warning("[Leaderboard] Erro HTTP %s do Supabase: %s", e.code, error_body)
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
def buscar_top10(category: str = "normal_speedrun") -> list[dict]:
    """Top 10 de uma categoria. Lista vazia em falha ou categoria vazia.

    Para speedrun: ordena por `tempo` ASC (menor = melhor).
    Para waves: ordena por `valor` DESC (maior = melhor).
    """
    cfg = CATEGORIAS.get(category, CATEGORIAS["normal_speedrun"])
    campo = cfg["campo"]
    ordem = cfg["ordem"]
    endpoint = (
        f"{TABELA}?select=nome,tempo,valor,created_at,player_id"
        f"&category=eq.{category}"
        f"&order={campo}.{ordem}&limit={MAX_ENTRIES}"
    )
    resultado = _request("GET", endpoint)
    if not resultado:
        return []
    for e in resultado:
        e["data"] = _formatar_data_utc(e.get("created_at"))
    return resultado

def buscar_record_proprio(category: str = "normal_speedrun") -> dict | None:
    """Retorna {'nome': ..., 'tempo': ...} do jogador atual na categoria, ou None."""
    player_id = _get_or_create_player_id()
    resultado = _request(
        "GET",
        f"{TABELA}?player_id=eq.{player_id}&category=eq.{category}&select=nome,tempo",
    )
    if resultado:
        return resultado[0]
    return None


def _upsert_seguro(player_id: str, category: str, entrada: dict) -> None:
    """PATCH se já existe entrada para player_id+category; POST caso contrário.

    Workaround para DB com PK em player_id sozinho: evita o 409 do on_conflict
    composto enquanto a migration (PK → player_id,category) não é executada.
    """
    # Tenta PATCH primeiro: só afeta linhas que combinam player_id E category.
    resultado = _request(
        "PATCH",
        f"{TABELA}?player_id=eq.{player_id}&category=eq.{category}",
        entrada,
    )
    # PATCH retorna lista vazia quando nenhuma linha casou — significa que
    # é um player_id novo NESSA categoria: insere via POST simples.
    if isinstance(resultado, list) and len(resultado) == 0:
        _request("POST", TABELA, entrada)


def registrar_vitoria(
    nome: str,
    tempo_segundos: float,
    category: str = "normal_speedrun",
) -> int | None:
    """Registra vitória com categoria e retorna posição no top 10.

    Retrocompatível: callers que não passam `category` usam 'normal_speedrun'.
    O banco tem trigger que só aceita UPDATE quando o novo tempo é menor.
    """
    player_id = _get_or_create_player_id()
    nome_sanitizado = nome[:16].strip() or "Anônimo"
    novo_tempo = round(tempo_segundos, 1)

    # Busca entrada existente na categoria para comparar tempos.
    existente = _request(
        "GET",
        f"{TABELA}?player_id=eq.{player_id}&category=eq.{category}&select=tempo",
    )
    if existente:
        tempo_salvo = existente[0].get("tempo", float("inf"))
        if novo_tempo >= tempo_salvo:
            # Não melhorou: apenas retorna posição atual, sem tocar no banco.
            top = buscar_top10(category)
            for i, e in enumerate(top):
                if e.get("player_id") == player_id:
                    return i + 1
            return None

    entrada = {
        "nome": nome_sanitizado,
        "tempo": novo_tempo,
        "valor": novo_tempo,
        "player_id": player_id,
        "category": category,
    }
    _upsert_seguro(player_id, category, entrada)

    top = buscar_top10(category)
    for i, e in enumerate(top):
        if e.get("player_id") == player_id:
            return i + 1
    return None


def _get_service_key() -> str:
    """Chave service_role do Supabase, lida de ~/.config/speedvslabubu/admin_key.

    Se ausente, retorna a anon key (ops de DELETE/UPDATE podem ser rejeitadas
    pelo RLS). Coloque a service_role key no arquivo para acesso total via admin.
    """
    try:
        key_path = _get_player_id_path().parent / "admin_key"
        if key_path.exists():
            k = key_path.read_text(encoding="utf-8").strip()
            if k:
                return k
    except Exception:
        pass
    return SUPABASE_KEY


def _admin_headers() -> dict:
    key = _get_service_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def registrar_infinite_waves(nome: str, waves_completadas: int) -> int | None:
    """Registra score do modo infinito (waves totalmente completadas).

    Só atualiza se o novo score for maior que o salvo. Retorna posição no
    top 10 ou None se não entrou. Fallback silencioso — nunca trava o jogo.
    """
    player_id = _get_or_create_player_id()
    nome_sanitizado = nome[:16].strip() or "Anônimo"

    existente = _request(
        "GET",
        f"{TABELA}?player_id=eq.{player_id}&category=eq.infinite_waves&select=valor",
    )
    if existente:
        waves_salvas = int(existente[0].get("valor") or 0)
        if waves_completadas <= waves_salvas:
            top = buscar_top10("infinite_waves")
            for i, e in enumerate(top):
                if e.get("player_id") == player_id:
                    return i + 1
            return None

    entrada = {
        "nome": nome_sanitizado,
        "tempo": 0.0,
        "valor": waves_completadas,
        "player_id": player_id,
        "category": "infinite_waves",
    }
    _upsert_seguro(player_id, "infinite_waves", entrada)

    top = buscar_top10("infinite_waves")
    for i, e in enumerate(top):
        if e.get("player_id") == player_id:
            return i + 1
    return None


def admin_deletar(player_id: str) -> bool:
    """Remove entrada do leaderboard pelo player_id. Requer service_role key."""
    url = f"{SUPABASE_URL}/rest/v1/{TABELA}?player_id=eq.{player_id}"
    req = urllib.request.Request(url, headers=_admin_headers(), method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=5, context=_SSL_CTX) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        logger.warning("[Admin] Erro HTTP %s ao deletar: %s", e.code, e.read().decode())
        return False
    except Exception as e:
        logger.warning("[Admin] Erro ao deletar: %s", e)
        return False


def admin_upsert(nome: str, tempo: float, player_id: str, category: str = "normal_speedrun") -> bool:
    """Insere ou atualiza entrada no leaderboard (conflict merge por player_id)."""
    entrada = {
        "nome": nome[:16].strip() or "Admin",
        "tempo": round(float(tempo), 1),
        "player_id": player_id,
        "category": category,
    }
    headers = _admin_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    url = f"{SUPABASE_URL}/rest/v1/{TABELA}?on_conflict=player_id"
    data = json.dumps(entrada).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5, context=_SSL_CTX):
            return True
    except urllib.error.HTTPError as e:
        logger.warning("[Admin] Erro HTTP %s ao upsert: %s", e.code, e.read().decode())
        return False
    except Exception as e:
        logger.warning("[Admin] Erro ao upsert: %s", e)
        return False


def formatar_tempo(segundos: float | int | None) -> str:
    """Formata segundos como MM:SS.d (décimos). Blindado contra None/str."""
    if segundos is None:
        segundos = 0.0
    try:
        s = float(segundos)
    except (ValueError, TypeError):
        s = 0.0
        
    total_decimos = int(round(s * 10))
    m = total_decimos // 600
    sec = (total_decimos % 600) // 10
    d = total_decimos % 10
    return f"{m:02d}:{sec:02d}.{d}"