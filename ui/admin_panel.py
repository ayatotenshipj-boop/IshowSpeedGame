"""Painel de administrador — acesso restrito ao player_id do dono.

Modal seguindo o protocolo de sub-painel:
  handle_event(event) → 'close' | None
  draw(surface)
  destroy()

Três abas: TC (TexasCoin), LEADERBOARD, CARTAS.
"""

import logging
import subprocess

import pygame
from core.asset_manager import AssetManager
import pygame_gui

from config.settings import (
    # CORREÇÃO: CENTRO_X e COLOR_GOLD removidos (não existem no settings.py)
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    COR_CINZA_CLARO,
    COR_DOURADO,
    COR_FUNDO_MODAL,
    COR_BORDA_MODAL,
    COR_BORDA_MODAL_TOPO,
    COR_HUD_BORDA,
    COR_LABEL_HUD,
    COR_OVERLAY_MODAL,
    COR_TEXTO_PRIMARIO,
    COR_VERDE_NEON,
    COR_VERMELHO,
)
from core import texas_coins
from core import leaderboard as lb

logger = logging.getLogger(__name__)

ADMIN_ID = "217481e7-d93b-431f-a351-a8a5c6690166"
ABAS = ["TC", "LEADERBOARD", "CARTAS"]
PAINEL_W = 740
PAINEL_H = 510


def _copiar_clipboard(texto: str) -> bool:
    """Copia para área de transferência (Linux: wl-copy / xclip / xsel)."""
    for cmd in (
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ):
        try:
            subprocess.run(cmd, input=texto.encode(), check=True,
                           timeout=2, capture_output=True)
            return True
        except Exception:
            continue
    return False


class AdminPanel:
    """Modal de administração com abas: TC | LEADERBOARD | CARTAS."""

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self._manager = manager
        self._fonte_titulo = AssetManager.get_font("font_title", 22)
        self._fonte = AssetManager.get_font("font_body", 15)
        self._fonte_peq = AssetManager.get_font("font_body", 12)

        self._overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill(COR_OVERLAY_MODAL)

        self._painel = pygame.Rect(0, 0, PAINEL_W, PAINEL_H)
        # CORREÇÃO: CENTRO_X substituído por WINDOW_WIDTH // 2
        self._painel.center = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        px, py = self._painel.x, self._painel.y

        self._aba_ativa = -1  # forçar _set_aba(0) no fim do __init__
        self._msg = ""
        self._msg_cor = COR_VERDE_NEON

        # ── Aba tabs (rects clicáveis pygame puro) ──────────────────────
        aba_w = 120
        self._aba_rects = [
            pygame.Rect(px + 10 + i * (aba_w + 6), py + 58, aba_w, 30)
            for i in range(len(ABAS))
        ]

        # ── Aba TC ──────────────────────────────────────────────────────
        self._entry_tc = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(px + 130, py + 145, 110, 36),
            manager=manager,
        )
        self._entry_tc.set_text("10")
        self._btn_tc_add = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(px + 250, py + 145, 80, 36),
            text="+ADD", manager=manager,
        )
        self._btn_tc_sub = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(px + 340, py + 145, 80, 36),
            text="-SUB", manager=manager,
        )
        self._btn_tc_set = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(px + 430, py + 145, 80, 36),
            text="=SET", manager=manager,
        )

        # ── Aba Leaderboard ─────────────────────────────────────────────
        self._lb_data: list[dict] = []
        self._lb_sel = -1
        self._lb_row_h = 27
        self._lb_area = pygame.Rect(px + 8, py + 110, PAINEL_W - 16, 6 * 27)

        self._entry_lb_nome = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(px + 8, py + 330, 150, 32),
            manager=manager,
        )
        self._entry_lb_tempo = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(px + 168, py + 330, 85, 32),
            manager=manager,
        )
        self._entry_lb_pid = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(px + 263, py + 330, 260, 32),
            manager=manager,
        )
        self._btn_lb_refresh = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(px + 533, py + 330, 100, 32),
            text="REFRESH", manager=manager,
        )
        self._btn_lb_del = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(px + 8, py + 374, 130, 36),
            text="DELETAR", manager=manager,
        )
        self._btn_lb_upsert = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(px + 148, py + 374, 180, 36),
            text="INSERIR / EDITAR", manager=manager,
        )

        # ── Aba Cartas ──────────────────────────────────────────────────
        self._cartas_data: list[str] = []
        self._cartas_sel = -1
        self._cartas_row_h = 28
        self._cartas_area = pygame.Rect(px + 8, py + 110, PAINEL_W - 16, 180)

        self._entry_carta = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(px + 8, py + 310, 230, 36),
            manager=manager,
        )
        self._entry_carta.set_text("speed_placeholder")
        self._btn_carta_add = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(px + 248, py + 310, 130, 36),
            text="ADICIONAR", manager=manager,
        )
        self._btn_carta_del = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(px + 388, py + 310, 130, 36),
            text="REMOVER", manager=manager,
        )

        # ── Botão Fechar ────────────────────────────────────────────────
        self.botao_fechar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(self._painel.centerx - 80,
                                      self._painel.bottom - 52, 160, 42),
            text="FECHAR", manager=manager,
        )

        self._set_aba(0)

    # ------------------------------------------------------------------ #
    # Gestão de abas
    # ------------------------------------------------------------------ #
    def _elems_tc(self):
        return (self._entry_tc, self._btn_tc_add, self._btn_tc_sub, self._btn_tc_set)

    def _elems_lb(self):
        return (self._entry_lb_nome, self._entry_lb_tempo, self._entry_lb_pid,
                self._btn_lb_refresh, self._btn_lb_del, self._btn_lb_upsert)

    def _elems_cartas(self):
        return (self._entry_carta, self._btn_carta_add, self._btn_carta_del)

    def _set_aba(self, idx: int) -> None:
        if idx == self._aba_ativa:
            return
        self._aba_ativa = idx
        self._msg = ""
        for e in self._elems_tc():
            e.show() if idx == 0 else e.hide()
        for e in self._elems_lb():
            e.show() if idx == 1 else e.hide()
        for e in self._elems_cartas():
            e.show() if idx == 2 else e.hide()

        if idx == 0:
            pass
        elif idx == 1:
            self._lb_refresh()
        elif idx == 2:
            self._cartas_data = list(texas_coins.get_itens())

    def _lb_refresh(self) -> None:
        self._lb_data = lb.buscar_top10()
        self._lb_sel = -1
        n = len(self._lb_data)
        self._set_msg(f"{n} entradas carregadas" if n else "Sem dados (offline?)")

    def _set_msg(self, texto: str, ok: bool = True) -> None:
        self._msg = texto
        self._msg_cor = COR_VERDE_NEON if ok else COR_VERMELHO

    # ------------------------------------------------------------------ #
    # Eventos
    # ------------------------------------------------------------------ #
    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            btn = event.ui_element
            if btn == self.botao_fechar:
                return "close"
            if btn == self._btn_tc_add:
                self._tc_op("+")
            elif btn == self._btn_tc_sub:
                self._tc_op("-")
            elif btn == self._btn_tc_set:
                self._tc_op("=")
            elif btn == self._btn_lb_refresh:
                self._lb_refresh()
            elif btn == self._btn_lb_del:
                self._lb_del()
            elif btn == self._btn_lb_upsert:
                self._lb_upsert()
            elif btn == self._btn_carta_add:
                self._carta_add()
            elif btn == self._btn_carta_del:
                self._carta_del()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for i, rect in enumerate(self._aba_rects):
                if rect.collidepoint(pos) and i != self._aba_ativa:
                    self._set_aba(i)
                    return None
            if self._aba_ativa == 1:
                self._lb_click(pos)
            elif self._aba_ativa == 2:
                self._cartas_click(pos)

        return None

    # ── TC ops ──────────────────────────────────────────────────────────
    def _tc_op(self, op: str) -> None:
        try:
            val = int(self._entry_tc.get_text().strip())
        except ValueError:
            self._set_msg("Valor inválido — use inteiro", ok=False)
            return
        if op == "+":
            novo = texas_coins.adicionar(val)
            self._set_msg(f"+{val} TC  →  saldo: {novo} TC")
        elif op == "-":
            novo = texas_coins.remover(val)
            self._set_msg(f"-{val} TC  →  saldo: {novo} TC")
        elif op == "=":
            novo = texas_coins.admin_set_saldo(val)
            self._set_msg(f"Saldo definido: {novo} TC")

    # ── Leaderboard ops ─────────────────────────────────────────────────
    def _lb_click(self, pos: tuple) -> None:
        for i, entry in enumerate(self._lb_data):
            ry = self._lb_area.y + i * self._lb_row_h
            if pygame.Rect(self._lb_area.x, ry, self._lb_area.width, self._lb_row_h).collidepoint(pos):
                self._lb_sel = i
                self._entry_lb_nome.set_text(entry.get("nome", ""))
                self._entry_lb_tempo.set_text(str(entry.get("tempo", "")))
                self._entry_lb_pid.set_text(entry.get("player_id", ""))
                break

    def _lb_del(self) -> None:
        pid = self._entry_lb_pid.get_text().strip()
        if not pid and 0 <= self._lb_sel < len(self._lb_data):
            pid = self._lb_data[self._lb_sel].get("player_id", "")
        if not pid:
            self._set_msg("Selecione entrada ou informe player_id", ok=False)
            return
        ok = lb.admin_deletar(pid)
        if ok:
            self._set_msg(f"Deletado: {pid[:14]}...")
            self._lb_refresh()
        else:
            self._set_msg("Falha — adicione service_role key em admin_key", ok=False)

    def _lb_upsert(self) -> None:
        nome = self._entry_lb_nome.get_text().strip()
        pid = self._entry_lb_pid.get_text().strip()
        try:
            tempo = float(self._entry_lb_tempo.get_text().strip())
        except ValueError:
            self._set_msg("Tempo inválido (ex: 125.3)", ok=False)
            return
        if not nome or not pid:
            self._set_msg("Nome e player_id são obrigatórios", ok=False)
            return
        ok = lb.admin_upsert(nome, tempo, pid)
        if ok:
            self._set_msg(f"Salvo: {nome} ({lb.formatar_tempo(tempo)})")
            self._lb_refresh()
        else:
            self._set_msg("Falha no upsert (verifique admin_key)", ok=False)

    # ── Cartas ops ──────────────────────────────────────────────────────
    def _cartas_click(self, pos: tuple) -> None:
        for i, item in enumerate(self._cartas_data):
            ry = self._cartas_area.y + i * self._cartas_row_h
            if pygame.Rect(self._cartas_area.x, ry, self._cartas_area.width, self._cartas_row_h).collidepoint(pos):
                self._cartas_sel = i
                self._entry_carta.set_text(item)
                break

    def _carta_add(self) -> None:
        item = self._entry_carta.get_text().strip()
        if not item:
            self._set_msg("Nome do item obrigatório", ok=False)
            return
        texas_coins.admin_adicionar_item(item)
        self._cartas_data = list(texas_coins.get_itens())
        self._set_msg(f"Item adicionado: {item}")

    def _carta_del(self) -> None:
        item = (
            self._cartas_data[self._cartas_sel]
            if 0 <= self._cartas_sel < len(self._cartas_data)
            else self._entry_carta.get_text().strip()
        )
        if not item:
            self._set_msg("Selecione ou informe o item", ok=False)
            return
        ok = texas_coins.admin_remover_item(item)
        self._cartas_data = list(texas_coins.get_itens())
        self._cartas_sel = -1
        self._set_msg(f"Removido: {item}" if ok else f"Item não encontrado: {item}", ok=ok)

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._overlay, (0, 0))

        p = self._painel
        pygame.draw.rect(surface, COR_FUNDO_MODAL, p, border_radius=8)
        pygame.draw.rect(surface, COR_BORDA_MODAL, p, 1, border_radius=8)
        pygame.draw.line(surface, COR_BORDA_MODAL_TOPO, p.topleft, (p.right, p.top), 3)

        titulo = self._fonte_titulo.render("PAINEL ADMIN", True, COR_DOURADO)
        surface.blit(titulo, (p.x + 14, p.y + 14))

        pygame.draw.line(surface, COR_HUD_BORDA, (p.x, p.y + 52), (p.right, p.y + 52), 1)

        # Abas
        for i, (label, rect) in enumerate(zip(ABAS, self._aba_rects)):
            ativa = i == self._aba_ativa
            bg_cor = COR_DOURADO if ativa else COR_CINZA_CLARO
            txt_cor = (10, 8, 0) if ativa else COR_LABEL_HUD
            pygame.draw.rect(surface, bg_cor, rect, border_radius=4)
            txt = self._fonte.render(label, True, txt_cor)
            surface.blit(txt, txt.get_rect(center=rect.center))

        pygame.draw.line(surface, COR_HUD_BORDA, (p.x, p.y + 95), (p.right, p.y + 95), 1)

        if self._aba_ativa == 0:
            self._draw_tc(surface, p)
        elif self._aba_ativa == 1:
            self._draw_lb(surface, p)
        elif self._aba_ativa == 2:
            self._draw_cartas(surface, p)

        # Footer: divider + mensagem feedback
        pygame.draw.line(surface, COR_HUD_BORDA,
                         (p.x, p.bottom - 62), (p.right, p.bottom - 62), 1)
        if self._msg:
            msg_surf = self._fonte_peq.render(self._msg, True, self._msg_cor)
            surface.blit(msg_surf, (p.x + 10, p.bottom - 54))

    def _draw_tc(self, surface: pygame.Surface, p: pygame.Rect) -> None:
        saldo_atual = texas_coins.get_saldo()
        lbl = self._fonte.render(f"Saldo atual:  {saldo_atual} TC", True, COR_DOURADO)
        surface.blit(lbl, (p.x + 14, p.y + 108))

        lbl2 = self._fonte_peq.render("Quantidade:", True, COR_LABEL_HUD)
        surface.blit(lbl2, (p.x + 14, p.y + 154))

        dica = self._fonte_peq.render(
            "+ADD soma  |  -SUB subtrai  |  =SET define diretamente", True, COR_LABEL_HUD
        )
        surface.blit(dica, (p.x + 14, p.y + 200))

    def _draw_lb(self, surface: pygame.Surface, p: pygame.Rect) -> None:
        hdr = self._fonte_peq.render(
            f"  {'#':>2}  {'NOME':<18} {'TEMPO':>7}  PLAYER ID", True, COR_LABEL_HUD
        )
        surface.blit(hdr, (p.x + 10, p.y + 98))

        for i, entry in enumerate(self._lb_data):
            ry = self._lb_area.y + i * self._lb_row_h
            if ry + self._lb_row_h > self._lb_area.bottom:
                break
            sel = i == self._lb_sel
            row_rect = pygame.Rect(p.x + 4, ry, PAINEL_W - 8, self._lb_row_h)
            if sel:
                pygame.draw.rect(surface, (40, 40, 20), row_rect)
                pygame.draw.rect(surface, COR_DOURADO, row_rect, 1)

            nome = entry.get("nome", "?")[:16]
            # CORREÇÃO: Evita None vindo do banco de dados
            tempo_val = entry.get("tempo", 0) or 0
            tempo = lb.formatar_tempo(tempo_val)
            pid_trunc = entry.get("player_id", "")[:14] + "..."
            linha = f"  {i + 1:>2}  {nome:<18} {tempo:>7}  {pid_trunc}"
            cor = COR_DOURADO if sel else COR_TEXTO_PRIMARIO
            surface.blit(self._fonte_peq.render(linha, True, cor), (p.x + 8, ry + 7))

        if not self._lb_data:
            surface.blit(
                self._fonte.render("Sem dados (offline?)", True, COR_LABEL_HUD),
                (p.x + 14, self._lb_area.y + 70),
            )

        # Labels dos inputs
        for lbl_txt, lx in [("Nome:", p.x + 8), ("Tempo:", p.x + 168), ("Player ID:", p.x + 263)]:
            surface.blit(self._fonte_peq.render(lbl_txt, True, COR_LABEL_HUD), (lx, p.y + 318))

    def _draw_cartas(self, surface: pygame.Surface, p: pygame.Rect) -> None:
        hdr = self._fonte_peq.render(
            f"INVENTÁRIO  ({len(self._cartas_data)} itens)", True, COR_LABEL_HUD
        )
        surface.blit(hdr, (p.x + 10, p.y + 98))

        if not self._cartas_data:
            surface.blit(
                self._fonte.render("Nenhum item no inventário", True, COR_LABEL_HUD),
                (p.x + 14, self._cartas_area.y + 60),
            )
        else:
            for i, item in enumerate(self._cartas_data):
                ry = self._cartas_area.y + i * self._cartas_row_h
                if ry + self._cartas_row_h > self._cartas_area.bottom:
                    break
                sel = i == self._cartas_sel
                row_rect = pygame.Rect(p.x + 4, ry, PAINEL_W - 8, self._cartas_row_h)
                if sel:
                    pygame.draw.rect(surface, (40, 40, 20), row_rect)
                    pygame.draw.rect(surface, COR_DOURADO, row_rect, 1)
                cor = COR_DOURADO if sel else COR_TEXTO_PRIMARIO
                surface.blit(
                    self._fonte_peq.render(f"  {item}", True, cor),
                    (p.x + 10, ry + 8),
                )

        lbl = self._fonte_peq.render("Item:", True, COR_LABEL_HUD)
        surface.blit(lbl, (p.x + 10, p.y + 298))

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #
    def destroy(self) -> None:
        for e in (*self._elems_tc(), *self._elems_lb(), *self._elems_cartas(), self.botao_fechar):
            e.kill()