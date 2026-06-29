"""Tela de gerenciamento do deck ativo — selecionar quais torres usar na partida.

Dois painéis:
  Esquerdo — Deck ativo (DECK_SLOTS slots fixos, preenchidos com torres equipadas)
  Direito — Coleção (todas as torres + cartas obtidas via gacha)
Clique em carta da coleção + slot vazio: equipa.
Clique em torre equipada: desequipa (volta à coleção).
ESC: salva e retorna ao Lobby.
"""

import logging

import pygame
from core.asset_manager import AssetManager

from config.settings import (
    COLOR_GOLD,
    COR_BORDA_MODAL,
    COR_DOURADO,
    COR_FUNDO_MODAL,
    COR_FUNDO_TELA,
    COR_LABEL_HUD,
    COR_TEXTO,
    COR_VERDE_NEON,
    DECK_SLOTS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from core import texas_coins
from entities.tower import TOWER_TYPES

logger = logging.getLogger(__name__)

PAINEL_W: int = 560
PAINEL_H: int = 500
PAINEL_Y: int = 100
CARD_W: int = 100
CARD_H: int = 120
CARD_GAP: int = 10
SPRITE_SZ: int = 56


class DeckBuilderScreen:
    """Tela de deck building — dois painéis lado a lado."""

    def __init__(self, assets) -> None:
        self._assets = assets
        self._fonte_big = AssetManager.get_font("font_title", 42)
        self._fonte_hdr = AssetManager.get_font("font_title", 22)
        self._fonte_label = AssetManager.get_font("font_body", 12)

        # Deck carregado da persistência (lista de asset_names)
        self._deck: list[str] = texas_coins.get_deck()

        # Painéis
        cx = WINDOW_WIDTH // 2
        self._painel_deck = pygame.Rect(cx - PAINEL_W - 16, PAINEL_Y, PAINEL_W, PAINEL_H)
        self._painel_colecao = pygame.Rect(cx + 16, PAINEL_Y, PAINEL_W, PAINEL_H)

        # Slots do deck (esquerdo)
        self._slot_rects: list[pygame.Rect] = self._calcular_slots()

        # Rects e tipos da coleção — calculados uma vez no __init__
        self._tipos_colecao: list = self._tipos_disponiveis()
        self._colecao_rects: list[pygame.Rect] = self._calcular_colecao_rects()

        # Cache de sprites escalados
        self._sprites: dict[str, pygame.Surface] = {}
        for tipo in TOWER_TYPES:
            try:
                self._sprites[tipo.asset_name] = pygame.transform.smoothscale(
                    assets.get(tipo.asset_name), (SPRITE_SZ, SPRITE_SZ)
                )
            except KeyError:
                logger.warning("Asset ausente para '%s' no DeckBuilder.", tipo.asset_name)

    def _calcular_slots(self) -> list[pygame.Rect]:
        """Slots do deck em 2 linhas (4 + restante) para caber no painel."""
        cols = 4
        slots = []
        for i in range(DECK_SLOTS):
            col = i % cols
            row = i // cols
            row_count = cols if row == 0 else DECK_SLOTS - cols
            total_w = row_count * CARD_W + (row_count - 1) * CARD_GAP
            x0 = self._painel_deck.x + (self._painel_deck.width - total_w) // 2
            y0 = self._painel_deck.y + 70 + row * (CARD_H + CARD_GAP + 4)
            slots.append(pygame.Rect(x0 + col * (CARD_W + CARD_GAP), y0, CARD_W, CARD_H))
        return slots

    def _tipos_disponiveis(self) -> list:
        """Tipos de torres disponíveis na coleção do jogador."""
        from entities.driving_car_speed import DrivingCarSpeed
        itens_gacha = texas_coins.get_itens()
        resultado = []
        for tipo in TOWER_TYPES:
            if tipo is DrivingCarSpeed:
                if texas_coins.ITEM_DRIVING_CAR_SPEED not in itens_gacha:
                    continue
            resultado.append(tipo)
        return resultado

    def _calcular_colecao_rects(self) -> list[pygame.Rect]:
        """Calcula rects das cartas da coleção com base no painel e tipos disponíveis."""
        p = self._painel_colecao
        cols = max(1, (p.width - 32) // (CARD_W + CARD_GAP))
        rects = []
        for i in range(len(self._tipos_colecao)):
            col = i % cols
            row = i // cols
            x = p.x + 16 + col * (CARD_W + CARD_GAP)
            y = p.y + 60 + row * (CARD_H + CARD_GAP)
            rects.append(pygame.Rect(x, y, CARD_W, CARD_H))
        return rects

    # ------------------------------------------------------------------ #
    # Input
    # ------------------------------------------------------------------ #
    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna 'fechar' para sair, None para continuar."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._salvar()
            return "fechar"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            # Clique em slot do deck — desequipa
            for i, rect in enumerate(self._slot_rects):
                if rect.collidepoint(pos):
                    if i < len(self._deck):
                        self._deck.pop(i)
                    return None

            # Clique em carta da coleção — equipa se slot disponível
            for i, rect in enumerate(self._colecao_rects):
                if rect.collidepoint(pos) and i < len(self._tipos_colecao):
                    tipo = self._tipos_colecao[i]
                    if (tipo.asset_name not in self._deck
                            and len(self._deck) < DECK_SLOTS):
                        self._deck.append(tipo.asset_name)
                    return None

        return None

    def _salvar(self) -> None:
        texas_coins.salvar_deck(self._deck)

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        """Renderiza a tela completa de deck building."""
        surface.fill(COR_FUNDO_TELA)

        titulo = self._fonte_big.render("GERENCIAR DECK", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(WINDOW_WIDTH // 2, 52)))

        self._draw_painel(surface, self._painel_deck, "DECK ATIVO")
        self._draw_painel(surface, self._painel_colecao, "COLEÇÃO")
        self._draw_slots(surface)
        self._draw_colecao(surface)

        hint = self._fonte_label.render(
            "Coleção: clique para equipar  |  Deck: clique para desequipar  |  ESC: salvar e fechar",
            True, COR_LABEL_HUD,
        )
        surface.blit(hint, hint.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 28)))

    def _draw_painel(self, surface: pygame.Surface, rect: pygame.Rect, titulo: str) -> None:
        pygame.draw.rect(surface, COR_FUNDO_MODAL, rect)
        pygame.draw.rect(surface, COR_BORDA_MODAL, rect, 1)
        pygame.draw.line(surface, COLOR_GOLD, rect.topleft, (rect.right, rect.top), 3)
        hdr = self._fonte_hdr.render(titulo, True, COR_DOURADO)
        surface.blit(hdr, (rect.x + 16, rect.y + 14))

    def _draw_slots(self, surface: pygame.Surface) -> None:
        for i, rect in enumerate(self._slot_rects):
            asset_equipado = self._deck[i] if i < len(self._deck) else None
            pygame.draw.rect(surface, (16, 14, 3), rect)
            pygame.draw.rect(surface, COR_BORDA_MODAL, rect, 2)

            if asset_equipado and asset_equipado in self._sprites:
                sprite = self._sprites[asset_equipado]
                surface.blit(sprite, sprite.get_rect(center=(rect.centerx, rect.centery - 10)))
                tipo = next(
                    (t for t in TOWER_TYPES if t.asset_name == asset_equipado), None
                )
                if tipo:
                    nome = self._fonte_label.render(tipo.nome[:13], True, COR_TEXTO)
                    surface.blit(nome, nome.get_rect(centerx=rect.centerx, y=rect.bottom - 20))
            else:
                vazio = self._fonte_label.render(f"Slot {i + 1}", True, COR_LABEL_HUD)
                surface.blit(vazio, vazio.get_rect(center=rect.center))

    def _draw_colecao(self, surface: pygame.Surface) -> None:
        for i, (tipo, rect) in enumerate(zip(self._tipos_colecao, self._colecao_rects)):
            equipada = tipo.asset_name in self._deck
            cor_borda = COR_VERDE_NEON if equipada else COR_BORDA_MODAL
            pygame.draw.rect(surface, (16, 14, 3), rect)
            pygame.draw.rect(surface, cor_borda, rect, 2 if equipada else 1)

            if tipo.asset_name in self._sprites:
                sprite = self._sprites[tipo.asset_name]
                surface.blit(sprite, sprite.get_rect(center=(rect.centerx, rect.centery - 12)))

            nome_surf = self._fonte_label.render(tipo.nome[:13], True, COR_TEXTO)
            surface.blit(nome_surf, nome_surf.get_rect(centerx=rect.centerx, y=rect.bottom - 22))

            custo_surf = self._fonte_label.render(f"${tipo.cost}", True, COLOR_GOLD)
            surface.blit(custo_surf, (rect.x + 4, rect.y + 4))

    def destroy(self) -> None:
        """Salva o deck antes de destruir a tela."""
        self._salvar()
