"""Sistema de auto-update via arquivos raw do GitHub.

O jogo compilado (PyInstaller) verifica sozinho se há nova versão publicada no
repositório público e baixa apenas os arquivos que mudaram — sem o jogador
precisar de conta GitHub, Git ou Python. Usa apenas a stdlib (`urllib`).

Fluxo: `check_update()` compara o `version.json` remoto com o local; havendo
versão maior, `download_files()` baixa cada arquivo listado, `save_local_version()`
grava o novo manifesto e `restart_game()` reinicia o executável.

Toda operação de rede é defensiva: qualquer falha vira log em PT-BR + retorno
neutro, NUNCA uma exceção que derrube o jogo.
"""

import json
import logging
import os
import shutil
import ssl
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Callable

from config.settings import RAIZ_PROJETO

logger = logging.getLogger(__name__)


def _ssl_context() -> ssl.SSLContext:
    """Contexto SSL que funciona no exe PyInstaller (sem CA do sistema).

    Sem isto, todo HTTPS dentro do exe falha com CERTIFICATE_VERIFY_FAILED.
    Usa o CA bundle do `certifi` (incluído no build); fallback sem verificação
    se faltar — preferindo um update funcional a um update quebrado.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


_SSL_CTX = _ssl_context()

# --- Configuração do repositório (público) ------------------------------- #
GITHUB_USER = "ayatotenshipj-boop"
GITHUB_REPO = "IshowSpeedGame"
GITHUB_BRANCH = "main"
VERSION_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/"
    f"{GITHUB_BRANCH}/version.json"
)
RAW_BASE_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}"
)

# Timeout das requisições HTTP, em segundos (só para a checagem de versão; o
# download do executável é grande e usa o timeout padrão do socket).
_TIMEOUT = 5

# Callback de progresso por arquivo (assets): (nome, indice, total).
ProgressCb = Callable[[str, int, int], None]
# Callback de progresso por bytes (download do executável): (baixados, total).
BytesProgressCb = Callable[[int, int], None]


def get_platform_key() -> str:
    """Chave de plataforma usada em version.json['download_url']."""
    return "windows" if sys.platform == "win32" else "linux"


def _exe_path() -> Path:
    """Caminho do executável atual.

    Frozen: o próprio binário PyInstaller. Em dev (rodando via python), usa um
    placeholder na raiz do projeto — `apply_and_restart` se recusa a substituir
    fora do modo frozen, então o interpretador Python nunca é tocado.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return RAIZ_PROJETO / "SpeedVsLabubu"


def _versao_para_tupla(versao: str) -> tuple[int, ...]:
    """Converte '1.2.3' em (1, 2, 3) para comparação numérica campo a campo.

    Partes não numéricas viram 0 (tolerante a versões malformadas).
    """
    partes: list[int] = []
    for parte in str(versao).split("."):
        try:
            partes.append(int(parte))
        except ValueError:
            partes.append(0)
    return tuple(partes)


def _dir_destino() -> Path:
    """Diretório onde os arquivos baixados são gravados.

    Empacotado (`sys.frozen`): a pasta do executável — NUNCA dentro do bundle
    `_MEIPASS`, que é temporário e some ao fechar. Em dev: a raiz do projeto.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return RAIZ_PROJETO


class Updater:
    """Verifica e aplica atualizações a partir do GitHub raw."""

    def is_configured(self) -> bool:
        """True quando o repositório está configurado (usuário real definido)."""
        return GITHUB_USER != "SEU_USUARIO_AQUI"

    def _ler_versao_local(self) -> str:
        """Lê o campo 'version' do version.json local. '0.0.0' se ausente/ilegível."""
        # No bundle o version.json fica em RAIZ_PROJETO (_MEIPASS); fora dele,
        # pode já ter sido sobrescrito por uma atualização anterior na pasta do
        # executável — esta tem prioridade.
        candidatos = [_dir_destino() / "version.json", RAIZ_PROJETO / "version.json"]
        for caminho in candidatos:
            try:
                if caminho.is_file():
                    with caminho.open(encoding="utf-8") as f:
                        return str(json.load(f).get("version", "0.0.0"))
            except Exception as erro:  # noqa: BLE001 — leitura nunca pode crashar
                logger.warning("Falha ao ler versão local em %s: %s", caminho, erro)
        return "0.0.0"

    def check_update(self) -> dict | None:
        """Consulta o version.json remoto.

        Retorna o dict remoto se a versão remota for MAIOR que a local; `None`
        se igual/menor ou em qualquer erro de rede (jamais levanta exceção).
        """
        if not self.is_configured():
            logger.info("Updater não configurado: verificação ignorada.")
            return None
        try:
            req = urllib.request.Request(
                VERSION_URL, headers={"User-Agent": "SpeedVsLabubu-Updater"}
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT, context=_SSL_CTX) as resp:
                remoto = json.loads(resp.read().decode("utf-8"))
        except Exception as erro:  # noqa: BLE001 — rede nunca pode crashar o jogo
            logger.warning("Falha ao verificar atualização: %s", erro)
            return None

        versao_remota = str(remoto.get("version", "0.0.0"))
        versao_local = self._ler_versao_local()
        if _versao_para_tupla(versao_remota) > _versao_para_tupla(versao_local):
            logger.info(
                "Nova versão disponível: %s (local: %s).", versao_remota, versao_local
            )
            return remoto
        logger.info(
            "Já está na versão mais recente (local: %s, remota: %s).",
            versao_local,
            versao_remota,
        )
        return None

    def download_files(
        self, file_list: list[str], progress_cb: ProgressCb | None = None
    ) -> bool:
        """Baixa cada arquivo de `file_list` para a pasta de destino.

        `progress_cb(filename, index, total)` é chamado a cada arquivo (1-based).
        Retorna True se todos baixaram; False em qualquer falha (log em PT-BR).
        """
        destino_base = _dir_destino()
        total = len(file_list)
        for indice, arquivo in enumerate(file_list, start=1):
            if progress_cb is not None:
                try:
                    progress_cb(arquivo, indice, total)
                except Exception as erro:  # noqa: BLE001 — callback de UI não derruba o download
                    logger.warning("Erro no callback de progresso: %s", erro)
            url = f"{RAW_BASE_URL}/{arquivo}"
            destino = destino_base / arquivo
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "SpeedVsLabubu-Updater"}
                )
                with urllib.request.urlopen(req, timeout=_TIMEOUT, context=_SSL_CTX) as resp:
                    dados = resp.read()
                destino.parent.mkdir(parents=True, exist_ok=True)
                with destino.open("wb") as f:
                    f.write(dados)
                logger.info("Baixado: %s (%d/%d).", arquivo, indice, total)
            except Exception as erro:  # noqa: BLE001
                logger.error("Falha ao baixar %s: %s", arquivo, erro)
                return False
        return True

    def save_local_version(self, remote_dict: dict) -> None:
        """Sobrescreve o version.json local (pasta do executável) com o remoto."""
        destino = _dir_destino() / "version.json"
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            with destino.open("w", encoding="utf-8") as f:
                json.dump(remote_dict, f, ensure_ascii=False, indent=2)
            logger.info("version.json local atualizado em %s.", destino)
        except Exception as erro:  # noqa: BLE001
            logger.error("Falha ao gravar version.json local: %s", erro)

    def get_changelog(self, remote_dict: dict) -> str:
        """Texto de changelog do manifesto remoto (ou aviso padrão)."""
        return remote_dict.get("changelog", "Sem detalhes")

    # ------------------------------------------------------------------ #
    # Atualização por substituição do executável (--onefile)
    # ------------------------------------------------------------------ #
    def get_platform_key(self) -> str:
        """Chave de plataforma ('windows'/'linux') do download_url remoto."""
        return get_platform_key()

    def url_executavel(self, remote_dict: dict) -> str | None:
        """URL do executável novo para a plataforma atual, ou None se ausente."""
        urls = remote_dict.get("download_url")
        if not isinstance(urls, dict):
            return None
        return urls.get(self.get_platform_key())

    def download_executable(
        self, url: str, progress_cb: BytesProgressCb | None = None
    ) -> Path | None:
        """Baixa o novo executável para `<exe>.new` ao lado do executável atual.

        `progress_cb(bytes_baixados, total_bytes)` é chamado durante o download.
        Torna o arquivo executável (Linux). Retorna o caminho temporário, ou
        None em qualquer falha (o parcial é removido).
        """
        exe_path = _exe_path()
        tmp_path = exe_path.parent / (exe_path.name + ".new")

        def _reportar(baixados: int, total: int) -> None:
            if progress_cb is not None:
                try:
                    progress_cb(baixados, total)
                except Exception as erro:  # noqa: BLE001 — UI não derruba o download
                    logger.warning("Erro no callback de progresso: %s", erro)

        try:
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            # Stream com contexto SSL próprio (urlretrieve não aceita context, e
            # no exe PyInstaller a verificação padrão falha sem CA do sistema).
            req = urllib.request.Request(
                url, headers={"User-Agent": "SpeedVsLabubu-Updater"}
            )
            with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                baixados = 0
                with tmp_path.open("wb") as f:
                    while True:
                        bloco = resp.read(65536)
                        if not bloco:
                            break
                        f.write(bloco)
                        baixados += len(bloco)
                        _reportar(baixados, total)
            # Bit de execução no Linux/macOS (no Windows é no-op inofensivo).
            tmp_path.chmod(tmp_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            logger.info("Executável novo baixado em %s.", tmp_path)
            return tmp_path
        except Exception as erro:  # noqa: BLE001 — rede nunca crasha o jogo
            logger.error("Erro ao baixar executável: %s", erro)
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            return None

    def apply_and_restart(self, tmp_path: Path) -> None:
        """Substitui o executável atual pelo novo e reinicia o jogo.

        Linux: `shutil.move` direto (o binário em execução pode ser substituído
        no Linux) seguido de `os.execv`. Windows: um `.bat` espera o processo
        fechar, move o `.new` por cima e reabre — pois o Windows trava o .exe em
        uso. Em modo dev (não-frozen) recusa-se a substituir (protege o Python).
        """
        if not getattr(sys, "frozen", False):
            logger.warning(
                "Modo dev (não-frozen): substituição do executável ignorada. "
                "Arquivo baixado em %s.", tmp_path
            )
            return

        exe_path = Path(sys.executable)
        try:
            if sys.platform == "win32":
                # Windows trava o .exe em execução: delega a um batch que espera
                # o processo fechar, troca o binário e reabre o jogo.
                bat = exe_path.parent / "_update.bat"
                bat.write_text(
                    "@echo off\r\n"
                    "timeout /t 2 /nobreak >nul\r\n"
                    f'move /y "{tmp_path}" "{exe_path}"\r\n'
                    f'start "" "{exe_path}"\r\n'
                    'del "%~f0"\r\n'
                )
                subprocess.Popen(
                    ["cmd", "/c", str(bat)],
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    close_fds=True,
                )
                sys.exit(0)
            else:
                # Linux: substitui o binário e reinicia no mesmo processo.
                shutil.move(str(tmp_path), str(exe_path))
                os.execv(str(exe_path), [str(exe_path)] + sys.argv[1:])
        except Exception as erro:  # noqa: BLE001
            logger.error("Falha ao aplicar atualização/reiniciar: %s", erro)
