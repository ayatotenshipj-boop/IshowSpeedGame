"""Painel de inspeção de torre (status, upgrade e venda).

Camada de UI em Pygame puro: desenha um painel flutuante quando uma torre
posicionada está selecionada, mostrando seus status (dano, alcance, cadência),
o preview do próximo nível e botões de ação (Upgrade, Vender, e — conforme o
tipo — Ativar buff / Usar habilidade). Apenas render e mapeamento de clique:
a aplicação das ações (gastar moedas, subir nível, vender) fica no main/loop.
"""

import pygame
from core.asset_manager import AssetManager

from entities.driving_car_speed import DrivingCarSpeed
from entities.target_priority import TargetPriority

from config.settings import (
    COLOR_GOLD,
    COR_CIANO,
    COR_TEXTO,
    MAP_RECT,
    PANEL_WIDTH,
    UI_MARGIN,
    UPGRADE_BG_COLOR,
    UPGRADE_BORDA_COLOR,
    UPGRADE_BTN_BG,
    UPGRADE_BTN_BORDA,
    UPGRADE_TEXT_SECONDARY,
)

PANEL_W: int = PANEL_WIDTH
BTN_H: int = 30
BTN_GAP: int = 6
MARGEM: int = UI_MARGIN + 6  # margem interna = UI_MARGIN base + folga visual

# Cores do painel — derivadas de settings.py (paleta speedvslabubu_ui_v2.html).
COR_FUNDO_PAINEL: tuple = (*UPGRADE_BG_COLOR, 235)   # com alpha para SRCALPHA
COR_BORDA_PAINEL: tuple = UPGRADE_BORDA_COLOR
COR_BTN: tuple = UPGRADE_BTN_BG
COR_BTN_OFF: tuple = (18, 16, 2)
COR_STATS: tuple = UPGRADE_TEXT_SECONDARY
COR_VERDE: tuple = COR_CIANO
COR_SETA: tuple = COR_CIANO
COR_DESABILITADO: tuple = (55, 50, 20)


class TowerPanel:
    """Desenha e trata o painel de status/upgrade/venda de uma torre."""

    def __init__(self) -> None:
        self._fonte_titulo = AssetManager.get_font("font_title", 22)
        self._fonte_stats = AssetManager.get_font("font_body", 14)
        self._fonte_btn = AssetManager.get_font("font_title", 18)

    # ------------------------------------------------------------------ #
    # Layout (compartilhado por draw e handle_click)
    # ------------------------------------------------------------------ #
    def _botoes(self, tower) -> list[tuple[str, str, bool]]:
        """Lista de botões (action, label, habilitado) conforme o tipo/estado."""
        botoes: list[tuple[str, str, bool]] = []

        # Upgrade.
        if tower.can_upgrade():
            botoes.append(("upgrade", f"Upgrade  ${tower.upgrade_cost()}", True))
        else:
            botoes.append(("upgrade", "NÍVEL MÁXIMO", False))

        # Skill ativável (DrivingCarSpeed).
        if hasattr(tower, "activate_skill"):
            pct = round((tower._buff_mult() - 1) * 100)
            if getattr(tower, "skill_ativa", False):
                restante = getattr(tower, "skill_timer", 0.0)
                botoes.append(("activate_skill", f"SPA +{pct}% ATIVO  {restante:.0f}s", False))
            elif getattr(tower, "cooldown_timer", 0.0) > 0.0:
                botoes.append(("activate_skill", f"Cooldown {tower.cooldown_timer:.0f}s", False))
            else:
                botoes.append(("activate_skill", f"Ativar Buff SPA +{pct}%", True))

        # Buff (Speed5).
        if hasattr(tower, "activate_buff"):
            if getattr(tower, "buff_active", False):
                botoes.append(("buff", "Buff ativo", False))
            elif getattr(tower, "cooldown_timer", 0.0) > 0.0:
                botoes.append(("buff", f"Cooldown {tower.cooldown_timer:.0f}s", False))
            else:
                botoes.append(("buff", "Ativar buff", True))

        # Habilidade (Speed7).
        if hasattr(tower, "use_ability"):
            usada = getattr(tower, "ability_used", False)
            botoes.append(("ability", "Habilidade usada" if usada else "Usar habilidade", not usada))

        # Prioridade de alvo — exibida para torres que atiram; omitida para
        # DrivingCarSpeed (buffer puro) e Speed7 (hitkill sem alvo individual).
        nao_tem_alvo = isinstance(tower, DrivingCarSpeed) or hasattr(tower, "use_ability")
        if not nao_tem_alvo and hasattr(tower, "priority"):
            prioridade = getattr(tower, "priority", TargetPriority.FIRST)
            _LABELS_PRIORIDADE = {
                TargetPriority.FIRST:     "Alvo: Primeiro",
                TargetPriority.LAST:      "Alvo: Último",
                TargetPriority.STRONGEST: "Alvo: Mais Forte",
                TargetPriority.WEAKEST:   "Alvo: Mais Fraco",
            }
            label = _LABELS_PRIORIDADE.get(prioridade, "Alvo: Primeiro")
            botoes.append(("priority", label, True))

        # Vender + Fechar. Speed7 (única torre com `use_ability`) não é vendável:
        # vender+reimplantar burlaria o uso-único da habilidade global.
        if hasattr(tower, "use_ability"):
            botoes.append(("sell", "Não vendável", False))
        else:
            botoes.append(("sell", f"Vender  +${tower.sell_refund()}", True))
        botoes.append(("close", "Fechar", True))
        return botoes

    def _panel_rect(self, tower) -> pygame.Rect:
        """Retângulo do painel — âncora junto ao tile da torre com bounds check.

        Se a torre está perto da borda direita o painel espelha para a esquerda.
        Garante que o painel nunca vaza do MAP_RECT.
        """
        n = len(self._botoes(tower))
        altura = 112 + n * (BTN_H + BTN_GAP) + MARGEM

        # Posição pixel da torre (tower.x/y são coordenadas de render; fallback: borda direita).
        tx = int(getattr(tower, "x", MAP_RECT.right - PANEL_W - UI_MARGIN))

        # Verifica se cabe à direita do tile; se não, espelha para a esquerda.
        if tx + PANEL_W + UI_MARGIN <= MAP_RECT.right:
            x = tx + UI_MARGIN
        else:
            x = max(MAP_RECT.left, tx - PANEL_W - UI_MARGIN)

        # Ancora verticalmente próximo ao tile, clampado para não vazar embaixo.
        ty = int(getattr(tower, "y", MAP_RECT.y + 44))
        y = min(ty, MAP_RECT.bottom - altura - UI_MARGIN)
        y = max(y, MAP_RECT.y + 44)

        return pygame.Rect(x, y, PANEL_W, altura)

    def _btn_rects(self, tower) -> list[tuple[pygame.Rect, str, str, bool]]:
        """Rects dos botões com seus (action, label, habilitado)."""
        painel = self._panel_rect(tower)
        x = painel.x + MARGEM
        w = PANEL_W - 2 * MARGEM
        y = painel.y + 108
        res = []
        for action, label, on in self._botoes(tower):
            res.append((pygame.Rect(x, y, w, BTN_H), action, label, on))
            y += BTN_H + BTN_GAP
        return res

    # ------------------------------------------------------------------ #
    # Input
    # ------------------------------------------------------------------ #
    def handle_click(self, pos: tuple[int, int], tower) -> str | None:
        """Mapeia o clique: None se fora do painel, '' se dentro sem botão,
        senão a ação ('upgrade'|'buff'|'ability'|'sell'|'close')."""
        if not self._panel_rect(tower).collidepoint(pos):
            return None
        for rect, action, _label, _on in self._btn_rects(tower):
            if rect.collidepoint(pos):
                return action
        return ""  # clique no painel, fora de botões: consome sem ação

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface, tower, coins: int) -> None:
        """Desenha o painel com status, preview de upgrade e botões."""
        painel = self._panel_rect(tower)
        fundo = pygame.Surface(painel.size, pygame.SRCALPHA)
        fundo.fill(COR_FUNDO_PAINEL)
        surface.blit(fundo, painel.topleft)
        pygame.draw.rect(surface, COR_BORDA_PAINEL, painel, 2)
        # Faixa-topo 3px dourada — identidade visual dos painéis modais.
        pygame.draw.line(surface, COLOR_GOLD, painel.topleft, (painel.right, painel.top), 3)

        # Título.
        titulo = self._fonte_titulo.render(
            f"{tower.nome}   Nv.{tower.level}/3", True, COLOR_GOLD
        )
        surface.blit(titulo, (painel.x + MARGEM, painel.y + 12))

        # Status com preview do próximo nível.
        buff_ativo = getattr(tower, "buff_active", False)
        prox = tower.next_stats()
        dano_atual = tower.effective_damage() if hasattr(tower, "effective_damage") else tower.damage
        linhas: list[tuple[str, object, object]] = [
            ("Dano", dano_atual, None if prox is None else prox[0]),
            ("Alcance", tower.range_px, None if prox is None else prox[1]),
            ("Cadência", round(tower.fire_rate, 1), None if prox is None else round(prox[2], 1)),
        ]
        y = painel.y + 44
        for nome, atual, nxt in linhas:
            txt = self._fonte_stats.render(f"{nome}: {atual}", True, COR_STATS)
            surface.blit(txt, (painel.x + MARGEM, y))
            if nxt is not None and nxt != atual:
                seta = self._fonte_stats.render(f"-> {nxt}", True, COR_SETA)
                surface.blit(seta, (painel.x + MARGEM + 150, y))
            y += 20
        # Linha extra no modo buff AOE do Speed5.
        if buff_ativo and hasattr(tower, "BUFF_AOE_INTERVAL"):
            aoe_txt = self._fonte_stats.render(
                f"AOE 6s  range +20%", True, (255, 200, 60)
            )
            surface.blit(aoe_txt, (painel.x + MARGEM, y))

        # Botões.
        for rect, action, label, on in self._btn_rects(tower):
            habil = on
            if action == "upgrade" and on and coins < tower.upgrade_cost():
                habil = False  # sem moedas: aparência desabilitada
            cor_btn = COR_BTN if habil else COR_BTN_OFF
            pygame.draw.rect(surface, cor_btn, rect, border_radius=4)
            pygame.draw.rect(surface, UPGRADE_BTN_BORDA, rect, 1, border_radius=4)
            cor_txt = self._cor_label(action, habil)
            txt = self._fonte_btn.render(label, True, cor_txt)
            surface.blit(txt, txt.get_rect(center=rect.center))

    @staticmethod
    def _cor_label(action: str, habilitado: bool) -> tuple[int, int, int]:
        """Cor do texto do botão conforme ação e estado."""
        if not habilitado:
            return COR_DESABILITADO
        if action == "sell":
            return COR_VERDE
        return COR_TEXTO
