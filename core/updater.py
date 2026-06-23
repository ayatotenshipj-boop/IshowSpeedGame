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
import sys
import urllib.request
from pathlib import Path
from typing import Callable

from config.settings import RAIZ_PROJETO

logger = logging.getLogger(__name__)

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

# Timeout das requisições HTTP, em segundos.
_TIMEOUT = 5

ProgressCb = Callable[[str, int, int], None]


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
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
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
                with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
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

    def restart_game(self) -> None:
        """Reinicia o executável atual (aplica os arquivos recém-baixados)."""
        logger.info("Reiniciando o jogo para aplicar a atualização...")
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv[1:])
        except Exception as erro:  # noqa: BLE001
            logger.error("Falha ao reiniciar automaticamente: %s", erro)
