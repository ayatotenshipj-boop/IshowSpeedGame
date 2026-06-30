"""Tela de changelog ("Novidades da versão") — redesenhada.

Modal scrollável estilo HTML de referência:
  header dourado  →  Título "NOVIDADES" + botão [×]
  conteúdo scroll →  versão, data, seções [TAG] e itens "— texto"
  footer          →  botão [ENTENDIDO] (btn_primario)

Protocolo de overlay do menu: handle_event → bool (True ao fechar),
draw, destroy. Toda leitura de arquivo é defensiva.
"""

import json
import logging
import sys
from pathlib import Path

import pygame
from core.asset_manager import AssetManager
import pygame_gui

from config.settings import (
    COLOR_GOLD,
    COR_BORDA_SUTIL,
    COR_FUNDO_MODAL,
    COR_HUD_BORDA,
    COR_LABEL_HUD,
    COR_VERMELHO,
    RAIZ_PROJETO,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)

logger = logging.getLogger(__name__)

CENTRO_X: int = WINDOW_WIDTH // 2
CENTRO_Y: int = WINDOW_HEIGHT // 2

# Cores específicas do changelog (seguindo HTML de referência)
_COR_ITEM_TEXTO = (170, 170, 170)    # #aaa — texto dos itens
_COR_ITEM_BORDA = (13, 17, 23)       # #0d1117 — divisor abaixo de cada item
_COR_SECAO_BORDA = (30, 34, 41)      # #1e2229 — borda abaixo do título de seção
_COR_DASH        = (51, 51, 51)       # #333 — traço "—" antes do item
_COR_DATA        = (68, 68, 68)       # #444 — data da versão
_COR_X_NORMAL    = (102, 102, 102)   # #666 — botão fechar normal
_COR_X_BORDA     = (51, 51, 51)      # #333 — borda do botão fechar


# ── Funções utilitárias (ler version.json + controle "já visto") ─────────────

def _version_json_candidatos() -> list[Path]:
    candidatos = [RAIZ_PROJETO / "version.json"]
    if getattr(sys, "frozen", False):
        candidatos.insert(0, Path(sys.executable).parent / "version.json")
    return candidatos


def ler_version_json() -> dict:
    for caminho in _version_json_candidatos():
        try:
            if caminho.is_file():
                with caminho.open(encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao ler version.json em %s: %s", caminho, e)
    return {}


def _get_seen_path() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "speedvslabubu"
    else:
        base = Path.home() / ".config" / "speedvslabubu"
    base.mkdir(parents=True, exist_ok=True)
    return base / "changelog_seen"


def changelog_ja_visto(versao_atual: str) -> bool:
    if not versao_atual:
        return True
    try:
        path = _get_seen_path()
        if not path.exists():
            return False
        return path.read_text(encoding="utf-8").strip() == versao_atual
    except Exception:  # noqa: BLE001
        return True


def marcar_changelog_visto(versao_atual: str) -> None:
    if not versao_atual:
        return
    try:
        _get_seen_path().write_text(versao_atual, encoding="utf-8")
    except Exception:  # noqa: BLE001
        logger.warning("[Changelog] Não foi possível gravar changelog_seen.")


# ── Tela ─────────────────────────────────────────────────────────────────────

class ChangelogScreen:
    """Modal scrollável com as novidades da versão (overlay do menu)."""

    PAINEL_W  = 560
    PAINEL_H  = 540
    HEADER_H  = 56
    FOOTER_H  = 60
    CONTENT_H = PAINEL_H - HEADER_H - FOOTER_H   # 424px scrolláveis

    def __init__(
        self, manager: pygame_gui.UIManager, versao: str, changelog_texto: str
    ) -> None:
        self.versao = versao

        # Fontes
        self._fonte_titulo = AssetManager.get_font("font_title", 24)
        self._fonte_versao = AssetManager.get_font("font_title", 22)
        self._fonte_secao  = AssetManager.get_font("font_hud", 13)
        self._fonte_item   = AssetManager.get_font("font_body", 14)
        self._fonte_data   = AssetManager.get_font("font_body", 12)
        self._fonte_x      = AssetManager.get_font("font_hud", 18)

        # Posição do painel
        self._painel = pygame.Rect(0, 0, self.PAINEL_W, self.PAINEL_H)
        self._painel.center = (CENTRO_X, CENTRO_Y)

        # Rect do botão X (calculado uma vez)
        px, py = self._painel.x, self._painel.y
        self._x_rect = pygame.Rect(px + self.PAINEL_W - 44, py + 14, 28, 28)

        # Parse e pré-renderização do conteúdo
        self._secoes = self._parsear(changelog_texto)
        self._scroll_y  = 0
        self._content_surf: pygame.Surface | None = None
        self._content_h_total = 0
        self._build_content()

        # Botão ENTENDIDO (pygame_gui — btn_primario)
        btn_x = px + 16
        btn_y = py + self.HEADER_H + self.CONTENT_H + (self.FOOTER_H - 36) // 2
        self.botao_entendido = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(btn_x, btn_y, self.PAINEL_W - 32, 36),
            text="ENTENDIDO",
            manager=manager,
            object_id="#btn_primario",
        )

    # ── Parser ───────────────────────────────────────────────────────────────
    def _parsear(self, texto: str) -> list[dict]:
        """Converte texto plano em lista de seções.

        Formato suportado:
          Título da versão (primeira linha não-vazia e não-seção)
          [Nome da Seção]
          - Item da seção
        """
        secoes: list[dict] = []
        secao_atual: dict | None = None
        primeiro_titulo = True

        for linha in texto.split("\n"):
            linha = linha.rstrip()
            if not linha:
                continue
            if linha.startswith("[") and linha.endswith("]"):
                if secao_atual is not None:
                    secoes.append(secao_atual)
                secao_atual = {"titulo": linha[1:-1], "items": []}
            elif linha.startswith("- ") and secao_atual is not None:
                secao_atual["items"].append(linha[2:])
            elif primeiro_titulo:
                secoes.append({"titulo": "__HEADER__", "text": linha})
                primeiro_titulo = False

        if secao_atual is not None:
            secoes.append(secao_atual)
        return secoes

    # ── Pré-renderização ──────────────────────────────────────────────────────
    def _wrap(self, texto: str, fonte: pygame.font.Font, largura: int) -> list[str]:
        """Quebra `texto` em linhas que cabem em `largura` pixels."""
        palavras = texto.split(" ")
        linhas: list[str] = []
        atual = ""
        for p in palavras:
            tentativa = f"{atual} {p}".strip()
            if fonte.size(tentativa)[0] <= largura:
                atual = tentativa
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas or [""]

    def _build_content(self) -> None:
        """Gera a Surface com todo o conteúdo (pode ser maior que CONTENT_H)."""
        PAD_L      = 16
        LARG_CONT  = self.PAINEL_W - PAD_L - 12   # 12 para a barra de scroll
        LARG_ITEM  = LARG_CONT - 22                # menos espaço do traço
        ITEM_H     = 26
        SECAO_H    = 36  # header da seção (título + espaço)

        # Calcula altura total
        h = 16
        for s in self._secoes:
            if s["titulo"] == "__HEADER__":
                h += 32 + 20 + 20  # versão + data + gap
            else:
                h += SECAO_H
                for item in s["items"]:
                    linhas = self._wrap(item, self._fonte_item, LARG_ITEM)
                    h += ITEM_H * len(linhas) + 6
                h += 12  # gap entre seções
        h += 16  # padding bottom

        self._content_h_total = h
        surf = pygame.Surface((LARG_CONT, h), pygame.SRCALPHA)

        y = 16
        for s in self._secoes:
            if s["titulo"] == "__HEADER__":
                # Versão (Bebas Neue dourado)
                ver = self._fonte_versao.render(s["text"], True, COLOR_GOLD)
                surf.blit(ver, (0, y))
                y += 32
                # Data (monospace dim)
                data = self._fonte_data.render(self.versao or "Junho 2026", True, _COR_DATA)
                surf.blit(data, (0, y))
                y += 20 + 20  # data + gap
            else:
                # Título da seção — uppercase + borda inferior
                titulo_upper = s["titulo"].upper()
                t = self._fonte_secao.render(titulo_upper, True, COR_LABEL_HUD)
                surf.blit(t, (0, y + 2))
                pygame.draw.line(surf, _COR_SECAO_BORDA, (0, y + SECAO_H - 6), (LARG_CONT, y + SECAO_H - 6))
                y += SECAO_H

                for item in s["items"]:
                    linhas = self._wrap(item, self._fonte_item, LARG_ITEM)
                    # Traço "—" na primeira linha
                    dash = self._fonte_item.render("—", True, _COR_DASH)
                    surf.blit(dash, (0, y + 4))
                    for i, linha in enumerate(linhas):
                        txt = self._fonte_item.render(linha, True, _COR_ITEM_TEXTO)
                        surf.blit(txt, (22, y + 4 + i * ITEM_H))
                    item_h_total = ITEM_H * len(linhas) + 6
                    # Borda inferior do item
                    pygame.draw.line(surf, _COR_ITEM_BORDA,
                                     (0, y + item_h_total - 1), (LARG_CONT, y + item_h_total - 1))
                    y += item_h_total

                y += 12  # gap entre seções

        self._content_surf = surf

    # ── Eventos ──────────────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Retorna True para fechar o modal."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_entendido:
                return True

        # Scroll com roda do mouse (qualquer posição — modal é overlay total)
        if event.type == pygame.MOUSEWHEEL:
            max_scroll = max(0, self._content_h_total - self.CONTENT_H)
            self._scroll_y -= event.y * 24
            self._scroll_y = max(0, min(self._scroll_y, max_scroll))

        # Clique no X
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._x_rect.collidepoint(event.pos):
                return True

        return False

    # ── Render ────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface,
             mouse_pos: tuple[int, int] | None = None) -> None:
        # Overlay escuro
        ov = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 210))
        surface.blit(ov, (0, 0))

        p = self._painel
        px, py = p.x, p.y

        # Fundo do painel
        pygame.draw.rect(surface, COR_FUNDO_MODAL, p)
        pygame.draw.rect(surface, COR_BORDA_SUTIL, p, 1)
        # Borda dourada no topo (3px)
        pygame.draw.line(surface, COLOR_GOLD, (px, py), (px + self.PAINEL_W, py), 3)

        # ── Header ───────────────────────────────────────────────────────────
        titulo_s = self._fonte_titulo.render("NOVIDADES", True, COLOR_GOLD)
        surface.blit(titulo_s, (px + 20, py + (self.HEADER_H - titulo_s.get_height()) // 2))
        # Separador header/content
        pygame.draw.line(surface, COR_HUD_BORDA,
                         (px, py + self.HEADER_H - 1), (px + self.PAINEL_W, py + self.HEADER_H - 1))

        # Botão ×
        mx, my = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
        x_hover = self._x_rect.collidepoint(mx, my)
        cor_x = COR_VERMELHO if x_hover else _COR_X_NORMAL
        cor_xb = COR_VERMELHO if x_hover else _COR_X_BORDA
        pygame.draw.rect(surface, (0, 0, 0, 0), self._x_rect)  # sem fundo
        pygame.draw.rect(surface, cor_xb, self._x_rect, 1)
        x_s = self._fonte_x.render("×", True, cor_x)
        surface.blit(x_s, x_s.get_rect(center=self._x_rect.center))

        # ── Conteúdo scrollável ───────────────────────────────────────────────
        content_top = py + self.HEADER_H
        clip = pygame.Rect(px, content_top, self.PAINEL_W, self.CONTENT_H)
        clip_surf = pygame.Surface((self.PAINEL_W, self.CONTENT_H))
        clip_surf.fill(COR_FUNDO_MODAL)
        if self._content_surf:
            clip_surf.blit(self._content_surf, (16, -int(self._scroll_y)))
        surface.blit(clip_surf, (px, content_top))

        # Scrollbar (quando conteúdo maior que área)
        if self._content_h_total > self.CONTENT_H:
            ratio     = self.CONTENT_H / max(1, self._content_h_total)
            bar_h     = max(28, int(self.CONTENT_H * ratio))
            max_scroll = max(1, self._content_h_total - self.CONTENT_H)
            bar_y     = int((self._scroll_y / max_scroll) * (self.CONTENT_H - bar_h))
            bar_rect  = pygame.Rect(px + self.PAINEL_W - 5, content_top + bar_y, 3, bar_h)
            pygame.draw.rect(surface, COR_LABEL_HUD, bar_rect, border_radius=1)

        # ── Footer ────────────────────────────────────────────────────────────
        footer_y = content_top + self.CONTENT_H
        pygame.draw.line(surface, COR_HUD_BORDA,
                         (px, footer_y), (px + self.PAINEL_W, footer_y))

    def destroy(self) -> None:
        self.botao_entendido.kill()
