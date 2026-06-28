"""Tela de Lobby — aparece após clicar JOGAR no menu principal.

Estado 'main': duas grandes caixas clicáveis (MODOS DE JOGO e STORE).
Estado 'modos': painel centralizado com os modos de jogo.
Estado 'store': painel centralizado com gacha de TexasCoin.

`handle_event` retorna "casual"|"voltar"|None.
"""

import pygame
import pygame_gui

from config.settings import (
    COLOR_GOLD,
    COR_BORDA_MODAL,
    COR_DOURADO,
    COR_FUNDO_MODAL,
    COR_FUNDO_TELA,
    COR_HUD_BORDA,
    COR_LABEL_HUD,
    COR_TEXTO,
    COR_VERDE_NEON,
    COR_VERMELHO,
    FONTE_TITULO_PATH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from core import texas_coins

CENTRO_X: int = WINDOW_WIDTH // 2

_PAD: int = 16

# Cards da tela main (dois grandes quadros clicáveis)
_CARD_W: int = 560
_CARD_H: int = 460
_CARD_Y: int = 130
_CARD_L: pygame.Rect = pygame.Rect(CENTRO_X - _CARD_W - 16, _CARD_Y, _CARD_W, _CARD_H)
_CARD_R: pygame.Rect = pygame.Rect(CENTRO_X + 16, _CARD_Y, _CARD_W, _CARD_H)

# Painel único dos sub-views (modos / store)
_SUB_X: int = 80
_SUB_W: int = WINDOW_WIDTH - 160
_SUB_Y: int = 80
_SUB_H: int = 560

# Botões de modo dentro do sub-view modos
_MODE_BTN_W: int = 500
_MODE_BTN_H: int = 56
_MODE_BTN_X: int = _SUB_X + (_SUB_W - _MODE_BTN_W) // 2


class LobbyScreen:
    """Lobby com navegação main → modos | store."""

    def __init__(self, manager: pygame_gui.UIManager, assets=None) -> None:
        self._manager = manager
        self._estado: str = "main"
        self._resultado_roll: dict | None = None
        self._sub = None   # MultijogadorScreen overlay
        self._mouse_pos: tuple[int, int] = (0, 0)

        self._fonte_big   = pygame.font.Font(str(FONTE_TITULO_PATH), 52)
        self._fonte_hdr   = pygame.font.Font(str(FONTE_TITULO_PATH), 28)
        self._fonte_card  = pygame.font.Font(str(FONTE_TITULO_PATH), 36)
        self._fonte_body  = pygame.font.SysFont("monospace", 14)
        self._fonte_label = pygame.font.SysFont("monospace", 12)
        self._fonte_coin  = pygame.font.Font(str(FONTE_TITULO_PATH), 28)

        # Fundo: mapa escurecido
        self._bg: pygame.Surface | None = None
        if assets is not None:
            try:
                bg = pygame.transform.smoothscale(
                    assets.get("mapa"), (WINDOW_WIDTH, WINDOW_HEIGHT)
                ).copy()
                dark = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                dark.fill((0, 0, 0, 195))
                bg.blit(dark, (0, 0))
                self._bg = bg
            except KeyError:
                pass

        self._coin_icon: pygame.Surface | None = None
        if assets is not None:
            try:
                self._coin_icon = pygame.transform.smoothscale(
                    assets.get("dialogs/victory_image"), (36, 36)
                )
            except KeyError:
                pass

        # ── Botões de modo (sub-view modos) ─────────────────────────────────
        y0 = _SUB_Y + 80
        gap = _MODE_BTN_H + 20

        self.btn_casual = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(_MODE_BTN_X, y0, _MODE_BTN_W, _MODE_BTN_H),
            text="CASUAL",
            manager=manager,
            object_id="#btn_primario",
        )
        self.btn_infinito = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(_MODE_BTN_X, y0 + gap, _MODE_BTN_W, _MODE_BTN_H),
            text="INFINITO  —  EM BREVE",
            manager=manager,
        )
        self.btn_infinito.disable()

        self.btn_multi = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(_MODE_BTN_X, y0 + gap * 2, _MODE_BTN_W, _MODE_BTN_H),
            text="MULTIJOGADOR",
            manager=manager,
        )

        # ── Botões de roll (sub-view store) ─────────────────────────────────
        roll_w = (_SUB_W - _PAD * 3) // 2
        roll_y = _SUB_Y + 300
        rx = _SUB_X + _PAD

        self.btn_roll_1x = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(rx, roll_y, roll_w, 46),
            text=f"1x ROLL  —  {texas_coins.PRECO_1X} TC",
            manager=manager,
        )
        self.btn_roll_10x = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(rx + roll_w + _PAD, roll_y, roll_w, 46),
            text=f"10x ROLL  —  {texas_coins.PRECO_10X} TC",
            manager=manager,
        )

        # ── Botão voltar (sempre visível) ────────────────────────────────────
        self.btn_voltar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 140, WINDOW_HEIGHT - 68, 280, 48),
            text="VOLTAR",
            manager=manager,
        )

        self._aplicar_estado("main")

    # ── Estado ───────────────────────────────────────────────────────────────
    def _aplicar_estado(self, estado: str) -> None:
        self._estado = estado
        for b in (self.btn_casual, self.btn_infinito, self.btn_multi,
                  self.btn_roll_1x, self.btn_roll_10x):
            b.hide()
        if estado == "modos":
            for b in (self.btn_casual, self.btn_infinito, self.btn_multi):
                b.show()
        elif estado == "store":
            self._atualizar_btns_roll()
            self.btn_roll_1x.show()
            self.btn_roll_10x.show()

    def _atualizar_btns_roll(self) -> None:
        saldo = texas_coins.get_saldo()
        (self.btn_roll_1x.enable if saldo >= texas_coins.PRECO_1X
         else self.btn_roll_1x.disable)()
        (self.btn_roll_10x.enable if saldo >= texas_coins.PRECO_10X
         else self.btn_roll_10x.disable)()

    # ── Input ────────────────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna 'casual'|'voltar' ou None."""
        if event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos

        if self._sub is not None:
            if self._sub.handle_event(event) == "close":
                self._sub.destroy()
                self._sub = None
                for b in (self.btn_casual, self.btn_infinito, self.btn_multi):
                    b.show()
            return None

        # Clique nas cards da tela main
        if (self._estado == "main"
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1):
            if _CARD_L.collidepoint(event.pos):
                self._aplicar_estado("modos")
                return None
            if _CARD_R.collidepoint(event.pos):
                self._aplicar_estado("store")
                return None

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_voltar:
                if self._estado == "main":
                    return "voltar"
                self._aplicar_estado("main")
                return None
            if event.ui_element == self.btn_casual:
                return "casual"
            if event.ui_element == self.btn_multi:
                from ui.menus import MultijogadorScreen
                self._sub = MultijogadorScreen(self._manager)
                for b in (self.btn_casual, self.btn_infinito, self.btn_multi):
                    b.hide()
            if event.ui_element == self.btn_roll_1x:
                self._resultado_roll = texas_coins.rolar(1)
                self._atualizar_btns_roll()
            if event.ui_element == self.btn_roll_10x:
                self._resultado_roll = texas_coins.rolar(10)
                self._atualizar_btns_roll()
        return None

    # ── Render ───────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        if self._bg is not None:
            surface.blit(self._bg, (0, 0))
        else:
            surface.fill(COR_FUNDO_TELA)

        title = self._fonte_big.render("SPEED VS LABUBU", True, COLOR_GOLD)
        surface.blit(title, title.get_rect(center=(CENTRO_X, 56)))

        if self._estado == "main":
            self._draw_main(surface)
        elif self._estado == "modos":
            self._draw_modos(surface)
        elif self._estado == "store":
            self._draw_store(surface)

        if self._sub is not None:
            self._sub.draw(surface)

    def _draw_card(self, surface: pygame.Surface, rect: pygame.Rect,
                   titulo: str, descricao: str, hover: bool) -> None:
        cor_fundo = (28, 24, 6) if hover else (18, 15, 3)
        cor_borda = COLOR_GOLD if hover else COR_BORDA_MODAL
        pygame.draw.rect(surface, cor_fundo, rect)
        pygame.draw.rect(surface, cor_borda, rect, 2 if hover else 1)
        pygame.draw.line(surface, COLOR_GOLD, rect.topleft, (rect.right, rect.top), 3)

        # Título centrado na metade superior
        txt = self._fonte_card.render(titulo, True, COLOR_GOLD if hover else COR_DOURADO)
        surface.blit(txt, txt.get_rect(centerx=rect.centerx, centery=rect.centery - 30))

        # Separador
        sx = rect.x + 40
        pygame.draw.line(surface, COR_HUD_BORDA,
                         (sx, rect.centery), (rect.right - 40, rect.centery), 1)

        desc = self._fonte_body.render(descricao, True,
                                        COR_TEXTO if hover else COR_LABEL_HUD)
        surface.blit(desc, desc.get_rect(centerx=rect.centerx, centery=rect.centery + 30))

        hint_cor = (180, 160, 80) if hover else (60, 55, 25)
        hint = self._fonte_label.render(
            ">> CLIQUE PARA ACESSAR <<" if hover else "Clique para acessar",
            True, hint_cor,
        )
        surface.blit(hint, hint.get_rect(centerx=rect.centerx, y=rect.bottom - 36))

    def _draw_main(self, surface: pygame.Surface) -> None:
        mx, my = self._mouse_pos
        self._draw_card(surface, _CARD_L, "MODOS DE JOGO",
                        "Casual  |  Infinito  |  Multiplayer",
                        _CARD_L.collidepoint(mx, my))
        self._draw_card(surface, _CARD_R, "STORE",
                        "Gacha  |  TexasCoin  |  Colecao",
                        _CARD_R.collidepoint(mx, my))

    def _draw_painel_sub(self, surface: pygame.Surface, titulo: str) -> pygame.Rect:
        p = pygame.Rect(_SUB_X, _SUB_Y, _SUB_W, _SUB_H)
        pygame.draw.rect(surface, COR_FUNDO_MODAL, p)
        pygame.draw.rect(surface, COR_BORDA_MODAL, p, 1)
        pygame.draw.line(surface, COLOR_GOLD, p.topleft, (p.right, p.top), 3)
        hdr = self._fonte_hdr.render(titulo, True, COR_DOURADO)
        surface.blit(hdr, (p.x + _PAD, p.y + 14))
        pygame.draw.line(surface, COR_HUD_BORDA, (p.x, p.y + 52), (p.right, p.y + 52), 1)
        return p

    def _draw_modos(self, surface: pygame.Surface) -> None:
        p = self._draw_painel_sub(surface, "MODOS DE JOGO")

        descs = [
            "Experiencia completa com selecao de dificuldade.",
            "Ondas infinitas — em breve!",
            "Enfrente outros jogadores — em breve!",
        ]
        y0 = _SUB_Y + 80
        gap = _MODE_BTN_H + 20
        for i, desc in enumerate(descs):
            txt = self._fonte_label.render(desc, True, COR_LABEL_HUD)
            surface.blit(txt, txt.get_rect(
                center=(_MODE_BTN_X + _MODE_BTN_W // 2, y0 + gap * i + _MODE_BTN_H + 9)
            ))

        earn_y = p.bottom - 110
        pygame.draw.line(surface, COR_HUD_BORDA, (p.x, earn_y - 8), (p.right, earn_y - 8), 1)
        lbl = self._fonte_label.render("Como ganhar TexasCoin:", True, COR_LABEL_HUD)
        surface.blit(lbl, (p.x + _PAD, earn_y))
        for i, (nome, qtd) in enumerate([
            ("Facil", 1), ("Normal", 5), ("Dificil", 15), ("Dificil 2x", 25),
        ]):
            linha = self._fonte_label.render(f"  {nome}: +{qtd} TC ao vencer", True, COR_TEXTO)
            surface.blit(linha, (p.x + _PAD, earn_y + 16 + i * 18))

    def _draw_store(self, surface: pygame.Surface) -> None:
        saldo = texas_coins.get_saldo()
        itens = texas_coins.get_itens()
        tem_item = texas_coins.PLACEHOLDER_ITEM in itens
        p = self._draw_painel_sub(surface, "STORE")

        # Saldo
        cx = p.x + _PAD
        cy = p.y + 64
        if self._coin_icon is not None:
            surface.blit(self._coin_icon, (cx, cy))
            cx += 44
        saldo_surf = self._fonte_coin.render(f"{saldo}  TexasCoin", True, COLOR_GOLD)
        surface.blit(saldo_surf, (cx, cy + 2))

        # Caixa de gacha
        gx, gy = p.x + _PAD, p.y + 116
        gw, gh = p.width - _PAD * 2, 170
        pygame.draw.rect(surface, (22, 20, 5), pygame.Rect(gx, gy, gw, gh))
        pygame.draw.rect(surface, (55, 46, 8), pygame.Rect(gx, gy, gw, gh), 1)
        pygame.draw.line(surface, (90, 70, 10), (gx, gy), (gx + gw, gy), 2)

        g_title = self._fonte_body.render("SPEED GACHA  [ PLACEHOLDER ]", True, COLOR_GOLD)
        surface.blit(g_title, (gx + _PAD, gy + 10))
        chance_lbl = self._fonte_label.render(
            f"Chance: 0.2% por roll  |  Itens obtidos: {len(itens)}/1",
            True, COR_LABEL_HUD,
        )
        surface.blit(chance_lbl, (gx + _PAD, gy + 28))

        slot = pygame.Rect(gx + _PAD, gy + 50, 72, 72)
        pygame.draw.rect(surface, (34, 28, 6), slot)
        pygame.draw.rect(surface, (80, 66, 14), slot, 1)
        if tem_item:
            ok = self._fonte_label.render("OBTIDO!", True, COR_VERDE_NEON)
            surface.blit(ok, ok.get_rect(center=slot.center))
        else:
            q = self._fonte_body.render("???", True, COR_LABEL_HUD)
            surface.blit(q, q.get_rect(center=slot.center))

        for i, (txt, cor) in enumerate([
            ("Speed Placeholder", COR_TEXTO),
            ("Um personagem misterioso...", COR_LABEL_HUD),
            ("(Sistema em construcao)", (50, 50, 50)),
        ]):
            s = self._fonte_label.render(txt, True, cor)
            surface.blit(s, (gx + _PAD + 80, gy + 50 + i * 18))

        if self._resultado_roll is not None:
            r = self._resultado_roll
            if "erro" in r:
                msg, cor = "Saldo insuficiente!", COR_VERMELHO
            elif r.get("ganhos"):
                msg = f"GANHOU! '{r['ganhos'][0]}' adicionado!"
                cor = COR_VERDE_NEON
            else:
                gasto = r.get("gasto", 0)
                n = gasto // texas_coins.PRECO_1X
                msg = f"Sorte na proxima! ({n}x roll — gastou {gasto} TC)"
                cor = COR_LABEL_HUD
            res = self._fonte_label.render(msg, True, cor)
            surface.blit(res, (gx + _PAD, gy + gh - 16))

        # Preço abaixo dos botões de roll
        preco_y = _SUB_Y + 300 + 46 + 10
        preco_txt = self._fonte_label.render(
            "1x = 10 TC  |  10x = 100 TC  (0.2% de chance por roll)",
            True, COR_LABEL_HUD,
        )
        surface.blit(preco_txt, preco_txt.get_rect(centerx=p.centerx, y=preco_y))

        # Inventário
        inv_y = _SUB_Y + 390
        pygame.draw.line(surface, COR_HUD_BORDA, (p.x, inv_y - 8), (p.right, inv_y - 8), 1)
        inv_hdr = self._fonte_label.render("INVENTARIO GACHA", True, COR_LABEL_HUD)
        surface.blit(inv_hdr, (p.x + _PAD, inv_y))
        if itens:
            for i, item in enumerate(itens):
                s = self._fonte_label.render(f"  + {item}", True, COR_VERDE_NEON)
                surface.blit(s, (p.x + _PAD, inv_y + 18 + i * 18))
        else:
            vazio = self._fonte_label.render("  Nenhum item obtido ainda.", True, (50, 50, 50))
            surface.blit(vazio, (p.x + _PAD, inv_y + 18))

    def destroy(self) -> None:
        if self._sub is not None:
            self._sub.destroy()
            self._sub = None
        for b in (self.btn_casual, self.btn_infinito, self.btn_multi,
                  self.btn_roll_1x, self.btn_roll_10x, self.btn_voltar):
            b.kill()
