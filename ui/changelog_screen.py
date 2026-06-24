"""Tela de changelog ("Novidades da versão").

Painel central em Pygame puro + botão ENTENDIDO via pygame_gui. Mostra o campo
`changelog` do version.json local (cada `\n` vira uma linha). Aparece UMA vez
automaticamente após uma atualização (controlado por um arquivo local que
guarda a última versão vista) e pode ser reaberto manualmente pelo botão [LOG]
no menu.

Segue o protocolo de overlay do menu: `handle_event` -> bool (True ao fechar),
`draw`, `destroy`. Toda leitura de arquivo é defensiva (nunca derruba o jogo).
"""

import json
import logging
import sys
from pathlib import Path

import pygame
import pygame_gui

from config.settings import (
    COLOR_GOLD,
    COLOR_HUD_BG,
    COR_TEXTO,
    RAIZ_PROJETO,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)

logger = logging.getLogger(__name__)

CENTRO_X: int = WINDOW_WIDTH // 2
CENTRO_Y: int = WINDOW_HEIGHT // 2


# --------------------------------------------------------------------------- #
# version.json local (versão + changelog)
# --------------------------------------------------------------------------- #
def _version_json_candidatos() -> list[Path]:
    """Caminhos onde o version.json local pode estar (prioriza pasta do exe).

    No bundle PyInstaller o version.json fica em RAIZ_PROJETO (_MEIPASS); fora
    dele, uma atualização pode ter gravado a versão nova na pasta do executável
    — esta tem prioridade (mesma regra do Updater).
    """
    candidatos = [RAIZ_PROJETO / "version.json"]
    if getattr(sys, "frozen", False):
        candidatos.insert(0, Path(sys.executable).parent / "version.json")
    return candidatos


def ler_version_json() -> dict:
    """Lê o version.json local; dict vazio se ausente/ilegível (nunca crasha)."""
    for caminho in _version_json_candidatos():
        try:
            if caminho.is_file():
                with caminho.open(encoding="utf-8") as f:
                    return json.load(f)
        except Exception as erro:  # noqa: BLE001 — leitura nunca pode crashar o jogo
            logger.warning("Falha ao ler version.json em %s: %s", caminho, erro)
    return {}


# --------------------------------------------------------------------------- #
# Estado "changelog já visto" (arquivo local por SO)
# --------------------------------------------------------------------------- #
def _get_seen_path() -> Path:
    """Caminho do arquivo que guarda a última versão de changelog vista."""
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "speedvslabubu"
    else:
        base = Path.home() / ".config" / "speedvslabubu"
    base.mkdir(parents=True, exist_ok=True)
    return base / "changelog_seen"


def changelog_ja_visto(versao_atual: str) -> bool:
    """True se o changelog desta `versao_atual` já foi visto (e marcado)."""
    if not versao_atual:
        return True  # sem versão conhecida: não força exibição automática
    try:
        path = _get_seen_path()
        if not path.exists():
            return False
        return path.read_text(encoding="utf-8").strip() == versao_atual
    except Exception:  # noqa: BLE001 — FS indisponível: trata como "já visto"
        return True


def marcar_changelog_visto(versao_atual: str) -> None:
    """Grava `versao_atual` como a última vista. Falha de FS é tolerada."""
    if not versao_atual:
        return
    try:
        _get_seen_path().write_text(versao_atual, encoding="utf-8")
    except Exception:  # noqa: BLE001 — não persistir não pode derrubar o jogo
        logger.warning("[Changelog] Não foi possível gravar changelog_seen.")


# --------------------------------------------------------------------------- #
# Tela
# --------------------------------------------------------------------------- #
class ChangelogScreen:
    """Painel 700×500 com as novidades da versão (overlay do menu)."""

    PAINEL_W: int = 700
    PAINEL_H: int = 500

    def __init__(
        self, manager: pygame_gui.UIManager, versao: str, changelog_texto: str
    ) -> None:
        self.versao = versao
        self._fonte_titulo = pygame.font.SysFont(None, 44, bold=True)
        self._fonte_versao = pygame.font.SysFont(None, 28, bold=True)
        self._fonte_linha = pygame.font.SysFont(None, 26)

        self._painel = pygame.Rect(0, 0, self.PAINEL_W, self.PAINEL_H)
        self._painel.center = (CENTRO_X, CENTRO_Y)

        # Cada `\n` do changelog vira uma linha; depois quebra por largura.
        brutas = [ln.rstrip() for ln in changelog_texto.split("\n")]
        self._linhas = self._quebrar_linhas([ln for ln in brutas if ln])

        self.botao_entendido = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 110, self._painel.bottom - 66, 220, 48),
            text="ENTENDIDO",
            manager=manager,
        )

    def _quebrar_linhas(self, linhas: list[str]) -> list[str]:
        """Quebra cada linha por largura para caber no painel (word-wrap simples)."""
        larg_max = self.PAINEL_W - 56  # margens laterais
        resultado: list[str] = []
        for linha in linhas:
            palavras = linha.split(" ")
            atual = ""
            for palavra in palavras:
                tentativa = f"{atual} {palavra}".strip()
                if self._fonte_linha.size(tentativa)[0] <= larg_max:
                    atual = tentativa
                else:
                    if atual:
                        resultado.append(atual)
                    atual = palavra
            resultado.append(atual)
        return resultado

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Retorna True quando ENTENDIDO é pressionado (o caller fecha + marca)."""
        if (
            event.type == pygame_gui.UI_BUTTON_PRESSED
            and event.ui_element == self.botao_entendido
        ):
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Escurece a tela, desenha o painel, título, versão e as linhas."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))
        pygame.draw.rect(surface, COLOR_HUD_BG, self._painel, border_radius=14)
        pygame.draw.rect(surface, COLOR_GOLD, self._painel, 3, border_radius=14)

        titulo = self._fonte_titulo.render("📋 NOVIDADES DA VERSÃO", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, self._painel.y + 40)))

        if self.versao:
            ver = self._fonte_versao.render(f"Versão {self.versao}", True, COR_TEXTO)
            surface.blit(ver, ver.get_rect(center=(CENTRO_X, self._painel.y + 76)))

        # Linhas do changelog, alinhadas à esquerda. Limita ao que cabe acima do
        # botão (evita invadir o rodapé); o resto é truncado com reticências.
        x = self._painel.x + 28
        y = self._painel.y + 108
        limite_y = self.botao_entendido.relative_rect.top - 14
        for linha in self._linhas:
            if y + 28 > limite_y:
                reticencias = self._fonte_linha.render("...", True, COR_TEXTO)
                surface.blit(reticencias, (x, y))
                break
            txt = self._fonte_linha.render(linha, True, COR_TEXTO)
            surface.blit(txt, (x, y))
            y += 30

    def destroy(self) -> None:
        """Remove o botão ENTENDIDO do UIManager."""
        self.botao_entendido.kill()
