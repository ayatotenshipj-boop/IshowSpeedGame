"""Telas de menu do jogo (pygame_gui).

Contém as telas Menu principal, Pause, Game Over e Victory. Os botões são
elementos do pygame_gui (desenhados pelo UIManager); cada tela desenha seu
próprio fundo/overlay e título com pygame puro. Único módulo, além da
inicialização em main.py, que usa pygame_gui.
"""

import pygame
import pygame_gui

from config.settings import (
    COLOR_GOLD,
    COR_TEXTO,
    COR_FUNDO_TELA,
    COR_FUNDO_MODAL,
    COR_OVERLAY_MODAL,
    COR_OVERLAY_BG_MENU,
    COR_OVERLAY_PAUSE,
    COR_SLIDER_TRACK,
    COR_SLIDER_HANDLE,
    COR_GAMEOVER_TITULO,
    COR_VICTORY_TITULO,
    COR_BANNER_FUNDO,
    COR_BANNER_DESC,
    COR_DOURADO_ESCURO,
    COR_LABEL_HUD,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    FONTE_TITULO_PATH,
)
from ui.conquistas_screen import ConquistasScreen

# Dimensões padrão dos botões.
BTN_W: int = 280
BTN_H: int = 60
CENTRO_X: int = WINDOW_WIDTH // 2


def _rect_centralizado(cy: int) -> pygame.Rect:
    """Retângulo de botão centralizado horizontalmente, com topo em `cy`."""
    return pygame.Rect(CENTRO_X - BTN_W // 2, cy, BTN_W, BTN_H)


class _EmBreveScreen:
    """Painel central genérico "Em breve..." com botão Fechar (sub-tela do menu).

    Usado por Conquistas e Multijogador. Não muda o estado do jogo: vive
    sobreposto ao menu principal. `handle_event` retorna 'close' ao fechar.
    """

    titulo: str = ""

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self._fonte_titulo = pygame.font.SysFont(None, 48)
        self._painel = pygame.Rect(0, 0, 600, 400)
        self._painel.center = (CENTRO_X, WINDOW_HEIGHT // 2)
        self._overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill(COR_OVERLAY_MODAL)
        self.botao_fechar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 90, self._painel.bottom - 80, 180, 50),
            text="Fechar",
            manager=manager,
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna 'close' quando o botão Fechar é pressionado."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_fechar:
                return "close"
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Escurece a tela e desenha o painel central com o título."""
        surface.blit(self._overlay, (0, 0))
        pygame.draw.rect(surface, COR_FUNDO_MODAL, self._painel, border_radius=12)
        pygame.draw.rect(surface, COLOR_GOLD, self._painel, 2, border_radius=12)
        txt = self._fonte_titulo.render(self.titulo, True, COR_TEXTO)
        surface.blit(txt, txt.get_rect(center=(CENTRO_X, self._painel.y + 90)))

    def destroy(self) -> None:
        """Remove o botão Fechar do UIManager."""
        self.botao_fechar.kill()


class MultijogadorScreen(_EmBreveScreen):
    """Painel de multijogador online (placeholder)."""

    titulo = "🌐 Multijogador Online — Em breve..."


class ConfiguracoesScreen:
    """Painel de Configurações com slider de volume da música (Pygame puro).

    Segue o protocolo de sub-painel do menu (`handle_event` -> 'close'|None,
    `draw`, `destroy`). O slider é arrastável: a posição X do handle mapeia para
    0.0–1.0 e chama `audio.set_volume`. O botão Fechar é do pygame_gui.
    """

    titulo: str = "⚙️ Configurações"

    # Geometria do slider (em espaço de render).
    TRACK_W: int = 300
    TRACK_H: int = 6
    HANDLE_R: int = 8

    def __init__(self, manager: pygame_gui.UIManager, audio=None) -> None:
        self._fonte_titulo = pygame.font.SysFont(None, 48)
        self._fonte = pygame.font.SysFont(None, 34)
        self._audio = audio
        self._painel = pygame.Rect(0, 0, 600, 400)
        self._painel.center = (CENTRO_X, WINDOW_HEIGHT // 2)
        self._overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill(COR_OVERLAY_MODAL)

        # Trilha do slider, centralizada no painel.
        self._track = pygame.Rect(
            CENTRO_X - self.TRACK_W // 2,
            self._painel.y + 190,
            self.TRACK_W,
            self.TRACK_H,
        )
        self._dragging: bool = False

        self.botao_fechar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 90, self._painel.bottom - 80, 180, 50),
            text="Fechar",
            manager=manager,
        )

    # ------------------------------------------------------------------ #
    # Slider helpers
    # ------------------------------------------------------------------ #
    def _valor(self) -> float:
        """Volume atual (0.0–1.0)."""
        return self._audio.volume_musica if self._audio is not None else 1.0

    def _handle_pos(self) -> tuple[int, int]:
        """Centro do handle conforme o volume atual."""
        x = self._track.x + int(self._valor() * self._track.width)
        return x, self._track.centery

    def _aplicar_de_x(self, mouse_x: int) -> None:
        """Converte uma posição X de mouse em volume e aplica via audio.set_volume."""
        frac = (mouse_x - self._track.x) / self._track.width
        frac = max(0.0, min(1.0, frac))
        if self._audio is not None:
            self._audio.set_volume(frac)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """'close' ao fechar; arrasto do slider ajusta o volume (sem fechar)."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_fechar:
                return "close"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Clique no handle ou em qualquer ponto da trilha captura o arrasto.
            hx, hy = self._handle_pos()
            sobre_handle = (event.pos[0] - hx) ** 2 + (event.pos[1] - hy) ** 2 <= (
                self.HANDLE_R + 4
            ) ** 2
            area_track = self._track.inflate(2 * self.HANDLE_R, 2 * self.HANDLE_R + 8)
            if sobre_handle or area_track.collidepoint(event.pos):
                self._dragging = True
                self._aplicar_de_x(event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._aplicar_de_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Escurece a tela, desenha o painel, o título e o slider de volume."""
        surface.blit(self._overlay, (0, 0))
        pygame.draw.rect(surface, COR_FUNDO_MODAL, self._painel, border_radius=12)
        pygame.draw.rect(surface, COLOR_GOLD, self._painel, 2, border_radius=12)

        titulo = self._fonte_titulo.render(self.titulo, True, COR_TEXTO)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, self._painel.y + 70)))

        rotulo = self._fonte.render("Volume da Música", True, COR_TEXTO)
        surface.blit(rotulo, rotulo.get_rect(center=(CENTRO_X, self._painel.y + 145)))

        # Trilha (cinza escuro) + preenchimento (dourado) até o handle.
        pygame.draw.rect(surface, COR_SLIDER_TRACK, self._track, border_radius=3)
        hx, hy = self._handle_pos()
        preenchido = pygame.Rect(
            self._track.x, self._track.y, hx - self._track.x, self._track.height
        )
        pygame.draw.rect(surface, COLOR_GOLD, preenchido, border_radius=3)
        # Handle (círculo dourado).
        pygame.draw.circle(surface, COLOR_GOLD, (hx, hy), self.HANDLE_R)
        pygame.draw.circle(surface, COR_SLIDER_HANDLE, (hx, hy), self.HANDLE_R, 2)

        # Porcentagem à direita do slider.
        pct = self._fonte.render(f"{int(round(self._valor() * 100))}%", True, COLOR_GOLD)
        surface.blit(pct, pct.get_rect(midleft=(self._track.right + 18, self._track.centery)))

    def destroy(self) -> None:
        """Remove o botão Fechar do UIManager."""
        self.botao_fechar.kill()


class MenuScreen:
    """Tela de menu principal: fundo do mapa, título com sombra e 4 botões."""

    def __init__(self, manager: pygame_gui.UIManager, assets=None, audio=None) -> None:
        self._manager = manager
        self._audio = audio
        self._fonte_titulo = pygame.font.Font(str(FONTE_TITULO_PATH), 110)

        # Fundo: mapa escurecido (ou fundo neutro se ausente).
        self._bg: pygame.Surface | None = None
        self._sprite_speed: pygame.Surface | None = None
        self._sprite_ancelotti: pygame.Surface | None = None
        if assets is not None:
            self._bg = self._carregar_bg(assets)
            self._sprite_speed = self._carregar_sprite(assets, "dialogs/speed-removebg-preview")
            self._sprite_ancelotti = self._carregar_sprite(assets, "dialogs/ancelotti-removebg-preview")

        # Botões centralizados.
        self.botao_jogar = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(240), text="JOGAR", manager=manager,
            object_id="#btn_primario",
        )
        self.botao_leaderboard = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(302), text="LEADERBOARD", manager=manager
        )
        self.botao_conquistas = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(364), text="CONQUISTAS", manager=manager
        )
        self.botao_multi = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(426), text="MULTIJOGADOR", manager=manager
        )
        self.botao_config = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(488), text="CONFIGURAÇÕES", manager=manager
        )
        self.botao_sair = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(550), text="SAIR", manager=manager
        )
        # Botão de atualização: menor que os demais, abaixo de SAIR.
        self.botao_atualizar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 100, 614, 200, 42),
            text="ATUALIZAR",
            manager=manager,
        )
        # Botão de changelog: pequeno, fixo no canto superior direito (emoji não
        # renderiza bem na fonte padrão, então usa texto "[LOG]").
        self.botao_changelog = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(WINDOW_WIDTH - 70, 10, 60, 28),
            text="[LOG]",
            manager=manager,
        )

        # Sub-painel "Em breve" aberto (Conquistas/Multijogador) ou None.
        self._sub: _EmBreveScreen | None = None

    @property
    def _botoes(self) -> tuple:
        """Todos os botões principais do menu (para hide/show/kill em lote)."""
        return (
            self.botao_jogar,
            self.botao_leaderboard,
            self.botao_conquistas,
            self.botao_multi,
            self.botao_config,
            self.botao_sair,
            self.botao_atualizar,
            self.botao_changelog,
        )

    def set_botoes_visiveis(self, visivel: bool) -> None:
        """Mostra/esconde todos os botões do menu (ex.: sob overlay de leaderboard)."""
        for b in self._botoes:
            b.show() if visivel else b.hide()

    @staticmethod
    def _carregar_bg(assets) -> pygame.Surface | None:
        """Mapa escalado e escurecido como fundo do menu."""
        try:
            bg = pygame.transform.smoothscale(
                assets.get("mapa"), (WINDOW_WIDTH, WINDOW_HEIGHT)
            ).copy()
        except KeyError:
            return None
        escuro = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        escuro.fill(COR_OVERLAY_BG_MENU)
        bg.blit(escuro, (0, 0))
        return bg

    @staticmethod
    def _carregar_sprite(assets, chave: str) -> pygame.Surface | None:
        """Retrato de personagem para os cantos (ausência tolerada)."""
        try:
            return pygame.transform.smoothscale(assets.get(chave), (260, 260))
        except KeyError:
            return None

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna 'play'|'quit'|'update'|None. Conquistas/Multijogador abrem sub-painel."""
        # Sub-painel aberto tem prioridade: só trata seu próprio Fechar.
        if self._sub is not None:
            if self._sub.handle_event(event) == "close":
                self._fechar_sub()
            return None

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_jogar:
                return "play"
            if event.ui_element == self.botao_sair:
                return "quit"
            if event.ui_element == self.botao_atualizar:
                return "update"
            if event.ui_element == self.botao_leaderboard:
                return "leaderboard"
            if event.ui_element == self.botao_changelog:
                return "changelog"
            if event.ui_element == self.botao_conquistas:
                self._abrir_sub(ConquistasScreen(self._manager))
            elif event.ui_element == self.botao_multi:
                self._abrir_sub(MultijogadorScreen(self._manager))
            elif event.ui_element == self.botao_config:
                self._abrir_sub(ConfiguracoesScreen(self._manager, self._audio))
        return None

    def _abrir_sub(self, sub: _EmBreveScreen) -> None:
        """Abre um sub-painel e ESCONDE os botões principais (senão ficam por cima)."""
        self._sub = sub
        for b in self._botoes:
            b.hide()

    def _fechar_sub(self) -> None:
        """Fecha o sub-painel e mostra de novo os botões principais."""
        if self._sub is not None:
            self._sub.destroy()
            self._sub = None
        for b in self._botoes:
            b.show()

    def draw(self, surface: pygame.Surface) -> None:
        """Fundo do mapa, sprites nos cantos, título com sombra e sub-painel."""
        if self._bg is not None:
            surface.blit(self._bg, (0, 0))
        else:
            surface.fill(COR_FUNDO_TELA)

        # Sprites nos cantos opostos (Ancelotti à esquerda, Speed à direita).
        if self._sprite_ancelotti is not None:
            surface.blit(self._sprite_ancelotti, (20, WINDOW_HEIGHT - 280))
        if self._sprite_speed is not None:
            surface.blit(
                self._sprite_speed, (WINDOW_WIDTH - 280, WINDOW_HEIGHT - 280)
            )

        # Título com sombra.
        sombra = self._fonte_titulo.render("SPEED VS LABUBU", True, COR_FUNDO_TELA)
        titulo = self._fonte_titulo.render("SPEED VS LABUBU", True, COLOR_GOLD)
        surface.blit(sombra, sombra.get_rect(center=(CENTRO_X + 4, 154)))
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, 150)))

        if self._sub is not None:
            self._sub.draw(surface)

    def destroy(self) -> None:
        """Remove os botões (e o sub-painel, se aberto) do UIManager."""
        if self._sub is not None:
            self._sub.destroy()
            self._sub = None
        for b in self._botoes:
            b.kill()


class PauseScreen:
    """Overlay de pause semi-transparente sobre o jogo."""

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self._fonte_titulo = pygame.font.Font(str(FONTE_TITULO_PATH), 72)
        self._overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._overlay.fill(COR_OVERLAY_PAUSE)
        self.botao_continuar = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(330), text="CONTINUAR", manager=manager,
            object_id="#btn_primario",
        )
        self.botao_menu = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(410),
            text="MENU PRINCIPAL",
            manager=manager,
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna 'resume', 'menu' ou None."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_continuar:
                return "resume"
            if event.ui_element == self.botao_menu:
                return "menu"
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Painel escuro semi-transparente cobrindo a tela + título."""
        surface.blit(self._overlay, (0, 0))
        titulo = self._fonte_titulo.render("PAUSA", True, COR_TEXTO)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, 230)))

    def destroy(self) -> None:
        """Remove os botões do UIManager."""
        self.botao_continuar.kill()
        self.botao_menu.kill()


class _EndScreen:
    """Base para telas de fim (Game Over / Victory)."""

    titulo: str = ""
    cor_titulo: tuple[int, int, int] = COR_TEXTO

    def __init__(self, manager: pygame_gui.UIManager) -> None:
        self._fonte_titulo = pygame.font.Font(str(FONTE_TITULO_PATH), 96)
        self.botao_retry = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(360),
            text="JOGAR NOVAMENTE",
            manager=manager,
            object_id="#btn_primario",
        )
        self.botao_menu = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(440),
            text="MENU PRINCIPAL",
            manager=manager,
        )

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Retorna 'retry', 'menu' ou None."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_retry:
                return "retry"
            if event.ui_element == self.botao_menu:
                return "menu"
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Fundo escuro + título grande."""
        surface.fill(COR_FUNDO_TELA)
        titulo = self._fonte_titulo.render(self.titulo, True, self.cor_titulo)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, 230)))

    def destroy(self) -> None:
        """Remove os botões do UIManager."""
        self.botao_retry.kill()
        self.botao_menu.kill()


class GameOverScreen(_EndScreen):
    """Tela de derrota — painel centralizado com stats, igual ao .vitoria-painel do HTML."""

    titulo = "GAME OVER"
    cor_titulo = COR_GAMEOVER_TITULO

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        kills: int = 0,
        coins: int = 0,
        lives: int = 0,
        onda_atual: int = 0,
        onda_total: int = 0,
        tempo: float = 0.0,
        modo: str = "NORMAL",
    ) -> None:
        super().__init__(manager)
        self._kills = kills
        self._coins = coins
        self._lives = lives
        self._onda_atual = onda_atual
        self._onda_total = onda_total
        self._tempo = tempo
        self._modo = modo.upper()
        self._fonte_titulo = pygame.font.Font(str(FONTE_TITULO_PATH), 80)
        self._fonte_msg = pygame.font.SysFont("monospace", 36)
        self._fonte_ph = pygame.font.SysFont("monospace", 22)
        self._fonte_sub = pygame.font.SysFont("monospace", 22)
        # Repositiona botões para dentro do painel (painel height=620, center y=360)
        self.botao_retry.set_relative_position((CENTRO_X - BTN_W // 2, 490))
        self.botao_menu.set_relative_position((CENTRO_X - BTN_W // 2, 558))

    def draw(self, surface: pygame.Surface) -> None:
        """Painel centralizado com border-top vermelho + stats (espelha .vitoria-painel)."""
        from core.leaderboard import formatar_tempo

        surface.fill(COR_FUNDO_TELA)

        painel = pygame.Rect(0, 0, 520, 620)
        painel.center = (CENTRO_X, WINDOW_HEIGHT // 2)
        pygame.draw.rect(surface, COR_FUNDO_MODAL, painel)
        pygame.draw.rect(surface, (80, 12, 10), painel, 1)
        pygame.draw.line(surface, COR_GAMEOVER_TITULO, painel.topleft, painel.topright, 3)

        titulo = self._fonte_titulo.render(self.titulo, True, self.cor_titulo)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, painel.y + 50)))

        sub = self._fonte_sub.render(
            f"Onda {self._onda_atual}/{self._onda_total}  ·  {self._modo}", True, COR_LABEL_HUD
        )
        surface.blit(sub, sub.get_rect(center=(CENTRO_X, painel.y + 100)))

        stats = [
            ("TEMPO", formatar_tempo(self._tempo), (136, 136, 136)),
            ("INIMIGOS", str(self._kills), COLOR_GOLD),
            ("VIDAS REST.", str(self._lives), COR_GAMEOVER_TITULO),
            ("MOEDAS", f"$ {self._coins}", (136, 136, 136)),
        ]
        grid_y = painel.y + 155
        grid_x = painel.x + 20
        col_w = (painel.width - 40) // 2
        for i, (label, valor, cor_val) in enumerate(stats):
            cx = grid_x + (i % 2) * col_w + col_w // 2
            cy = grid_y + (i // 2) * 72
            val_surf = self._fonte_msg.render(valor, True, cor_val)
            lbl_surf = self._fonte_ph.render(label, True, COR_LABEL_HUD)
            surface.blit(val_surf, val_surf.get_rect(center=(cx, cy)))
            surface.blit(lbl_surf, lbl_surf.get_rect(center=(cx, cy + 26)))


class VictoryScreen(_EndScreen):
    """Tela de vitória, com imagem de recompensa e estatísticas da partida."""

    titulo = "VITÓRIA!"
    cor_titulo = COR_VICTORY_TITULO

    # Dimensões da área da imagem de vitória (ou do placeholder).
    IMG_W: int = 420
    IMG_H: int = 200

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        kills: int,
        coins: int,
        victory_image: pygame.Surface | None = None,
        tempo: float = 0.0,
        nova_conquista: dict | None = None,
    ) -> None:
        super().__init__(manager)
        self._kills = kills
        self._coins = coins
        self._tempo = tempo
        # Banner exibido só quando a vitória desbloqueou uma conquista NOVA.
        self._nova_conquista = nova_conquista
        # Surface cacheada para o banner de conquista (tamanho fixo 376×104)
        self._banner_surf = pygame.Surface((376, 104), pygame.SRCALPHA)
        self._banner_surf.fill(COR_BANNER_FUNDO)
        self._fonte_titulo = pygame.font.Font(str(FONTE_TITULO_PATH), 80)
        self._fonte_msg = pygame.font.SysFont("monospace", 38)
        self._fonte_sub = pygame.font.SysFont("monospace", 28)
        self._fonte_stats = pygame.font.SysFont("monospace", 32)
        self._fonte_ph = pygame.font.SysFont("monospace", 24)

        # Imagem de vitória escalada para caber na área (ou None → placeholder).
        self._img: pygame.Surface | None = None
        if victory_image is not None:
            self._img = self._ajustar_imagem(victory_image)

        # Reposiciona os botões para o rodapé (abrem espaço p/ imagem + textos).
        self.botao_retry.set_relative_position((CENTRO_X - BTN_W // 2, 530))
        self.botao_menu.set_relative_position((CENTRO_X - BTN_W // 2, 598))

    def _ajustar_imagem(self, img: pygame.Surface) -> pygame.Surface:
        """Escala a imagem preservando proporção dentro de IMG_W×IMG_H."""
        iw, ih = img.get_size()
        if iw == 0 or ih == 0:
            return img  # imagem degenerada: usa como veio (evita div/0)
        fator = min(self.IMG_W / iw, self.IMG_H / ih)
        return pygame.transform.smoothscale(img, (int(iw * fator), int(ih * fator)))

    def draw(self, surface: pygame.Surface) -> None:
        """Painel centralizado com título, imagem, stats grid e banner de conquista."""
        from core.leaderboard import formatar_tempo

        surface.fill(COR_FUNDO_TELA)

        # Painel central estilizado (border-top 3px dourado, como HTML .vitoria-painel)
        painel = pygame.Rect(0, 0, 520, 660)
        painel.center = (CENTRO_X, WINDOW_HEIGHT // 2)
        pygame.draw.rect(surface, COR_FUNDO_MODAL, painel)
        pygame.draw.rect(surface, COR_DOURADO_ESCURO, painel, 1)
        pygame.draw.line(surface, COLOR_GOLD, painel.topleft, painel.topright, 3)

        titulo = self._fonte_titulo.render(self.titulo, True, self.cor_titulo)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, painel.y + 50)))

        # Imagem ou placeholder.
        area = pygame.Rect(0, 0, self.IMG_W, 140)
        area.center = (CENTRO_X, painel.y + 150)
        if self._img is not None:
            surface.blit(self._img, self._img.get_rect(center=area.center))
        else:
            pygame.draw.rect(surface, COR_DOURADO_ESCURO, area, 1)
            ph = self._fonte_ph.render("[ IMAGEM DE VITÓRIA ]", True, COLOR_GOLD)
            surface.blit(ph, ph.get_rect(center=area.center))

        # Stats em 2 colunas (como .vitoria-stats no HTML).
        stats = [
            ("INIMIGOS", str(self._kills)),
            ("MOEDAS", f"$ {self._coins}"),
        ]
        if self._tempo > 0:
            stats += [("TEMPO", formatar_tempo(self._tempo)), ("MODO", "NORMAL")]
        grid_y = painel.y + 250
        grid_x = painel.x + 20
        col_w = (painel.width - 40) // 2
        for i, (label, valor) in enumerate(stats):
            cx = grid_x + (i % 2) * col_w + col_w // 2
            cy = grid_y + (i // 2) * 72
            val_surf = self._fonte_msg.render(valor, True, COR_TEXTO)
            lbl_surf = self._fonte_ph.render(label, True, COR_LABEL_HUD)
            surface.blit(val_surf, val_surf.get_rect(center=(cx, cy)))
            surface.blit(lbl_surf, lbl_surf.get_rect(center=(cx, cy + 28)))

        if self._nova_conquista is not None:
            self._desenhar_banner_conquista(surface)

    def _desenhar_banner_conquista(self, surface: pygame.Surface) -> None:
        """Toast dourado no canto superior direito anunciando a conquista nova."""
        c = self._nova_conquista
        box = pygame.Rect(WINDOW_WIDTH - 396, 20, 376, 104)
        surface.blit(self._banner_surf, box.topleft)
        pygame.draw.rect(surface, COLOR_GOLD, box, 3, border_radius=10)

        titulo = self._fonte_sub.render("CONQUISTA DESBLOQUEADA!", True, COLOR_GOLD)
        surface.blit(titulo, (box.x + 16, box.y + 12))
        nome = self._fonte_sub.render(f'"{c["nome"]}"', True, COR_TEXTO)
        surface.blit(nome, (box.x + 16, box.y + 44))
        desc = self._fonte_ph.render(c["descricao"], True, COR_BANNER_DESC)
        surface.blit(desc, (box.x + 16, box.y + 74))
