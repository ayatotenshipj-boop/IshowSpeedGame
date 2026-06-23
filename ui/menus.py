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
    COLOR_HUD_BG,
    COR_TEXTO,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)

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
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        pygame.draw.rect(surface, COLOR_HUD_BG, self._painel, border_radius=12)
        pygame.draw.rect(surface, COLOR_GOLD, self._painel, 2, border_radius=12)
        txt = self._fonte_titulo.render(self.titulo, True, COR_TEXTO)
        surface.blit(txt, txt.get_rect(center=(CENTRO_X, self._painel.y + 90)))

    def destroy(self) -> None:
        """Remove o botão Fechar do UIManager."""
        self.botao_fechar.kill()


class ConquistasScreen(_EmBreveScreen):
    """Painel de conquistas (placeholder)."""

    titulo = "🏆 Conquistas — Em breve..."


class MultijogadorScreen(_EmBreveScreen):
    """Painel de multijogador online (placeholder)."""

    titulo = "🌐 Multijogador Online — Em breve..."


class ConfiguracoesScreen:
    """Painel de Configurações. Único controle: diminuir o volume da música.

    Segue o protocolo de sub-painel do menu (`handle_event` -> 'close'|None,
    `draw`, `destroy`). Chama `audio.abaixar_volume()` ao clicar no botão.
    """

    titulo: str = "⚙️ Configurações"

    def __init__(self, manager: pygame_gui.UIManager, audio=None) -> None:
        self._fonte_titulo = pygame.font.SysFont(None, 48)
        self._fonte = pygame.font.SysFont(None, 40)
        self._audio = audio
        self._painel = pygame.Rect(0, 0, 600, 400)
        self._painel.center = (CENTRO_X, WINDOW_HEIGHT // 2)
        self.botao_baixar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 140, self._painel.y + 170, 280, 56),
            text="🔉 Diminuir Música",
            manager=manager,
        )
        self.botao_fechar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 90, self._painel.bottom - 80, 180, 50),
            text="Fechar",
            manager=manager,
        )

    def _volume_pct(self) -> int:
        """Volume atual da música em porcentagem (0–100)."""
        if self._audio is None:
            return 100
        return int(round(self._audio.volume_musica * 100))

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """'close' ao fechar; diminui o volume e mantém aberto ao clicar baixar."""
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.botao_baixar:
                if self._audio is not None:
                    self._audio.abaixar_volume()
                return None
            if event.ui_element == self.botao_fechar:
                return "close"
        return None

    def draw(self, surface: pygame.Surface) -> None:
        """Escurece a tela, desenha o painel, o título e o volume atual."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        pygame.draw.rect(surface, COLOR_HUD_BG, self._painel, border_radius=12)
        pygame.draw.rect(surface, COLOR_GOLD, self._painel, 2, border_radius=12)

        titulo = self._fonte_titulo.render(self.titulo, True, COR_TEXTO)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, self._painel.y + 70)))

        vol = self._fonte.render(f"Volume da música: {self._volume_pct()}%", True, COLOR_GOLD)
        surface.blit(vol, vol.get_rect(center=(CENTRO_X, self._painel.y + 125)))

    def destroy(self) -> None:
        """Remove os botões do UIManager."""
        self.botao_baixar.kill()
        self.botao_fechar.kill()


class MenuScreen:
    """Tela de menu principal: fundo do mapa, título com sombra e 4 botões."""

    def __init__(self, manager: pygame_gui.UIManager, assets=None, audio=None) -> None:
        self._manager = manager
        self._audio = audio
        self._fonte_titulo = pygame.font.SysFont(None, 110, bold=True)

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
            relative_rect=_rect_centralizado(280), text="JOGAR", manager=manager
        )
        self.botao_conquistas = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(344), text="CONQUISTAS", manager=manager
        )
        self.botao_multi = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(408), text="MULTIJOGADOR", manager=manager
        )
        self.botao_config = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(472), text="CONFIGURAÇÕES", manager=manager
        )
        self.botao_sair = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(536), text="SAIR", manager=manager
        )
        # Botão de atualização: menor que os demais, abaixo de SAIR.
        self.botao_atualizar = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(CENTRO_X - 100, 600, 200, 42),
            text="🔄 Atualizar",
            manager=manager,
        )

        # Sub-painel "Em breve" aberto (Conquistas/Multijogador) ou None.
        self._sub: _EmBreveScreen | None = None

    @property
    def _botoes(self) -> tuple:
        """Todos os botões principais do menu (para hide/show/kill em lote)."""
        return (
            self.botao_jogar,
            self.botao_conquistas,
            self.botao_multi,
            self.botao_config,
            self.botao_sair,
            self.botao_atualizar,
        )

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
        escuro.fill((0, 0, 0, 150))
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
            surface.fill(COLOR_HUD_BG)

        # Sprites nos cantos opostos (Ancelotti à esquerda, Speed à direita).
        if self._sprite_ancelotti is not None:
            surface.blit(self._sprite_ancelotti, (20, WINDOW_HEIGHT - 280))
        if self._sprite_speed is not None:
            surface.blit(
                self._sprite_speed, (WINDOW_WIDTH - 280, WINDOW_HEIGHT - 280)
            )

        # Título com sombra.
        sombra = self._fonte_titulo.render("SPEED VS LABUBU", True, (0, 0, 0))
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
        self._fonte_titulo = pygame.font.SysFont(None, 72)
        self.botao_continuar = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(330), text="CONTINUAR", manager=manager
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
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 180))
        surface.blit(overlay, (0, 0))
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
        self._fonte_titulo = pygame.font.SysFont(None, 96)
        self.botao_retry = pygame_gui.elements.UIButton(
            relative_rect=_rect_centralizado(360),
            text="JOGAR NOVAMENTE",
            manager=manager,
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
        surface.fill(COLOR_HUD_BG)
        titulo = self._fonte_titulo.render(self.titulo, True, self.cor_titulo)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, 230)))

    def destroy(self) -> None:
        """Remove os botões do UIManager."""
        self.botao_retry.kill()
        self.botao_menu.kill()


class GameOverScreen(_EndScreen):
    """Tela de derrota."""

    titulo = "GAME OVER"
    cor_titulo = (220, 60, 60)


class VictoryScreen(_EndScreen):
    """Tela de vitória, com imagem de recompensa e estatísticas da partida."""

    titulo = "VITÓRIA!"
    cor_titulo = (80, 220, 90)

    # Dimensões da área da imagem de vitória (ou do placeholder).
    IMG_W: int = 420
    IMG_H: int = 200

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        kills: int,
        coins: int,
        victory_image: pygame.Surface | None = None,
    ) -> None:
        super().__init__(manager)
        self._kills = kills
        self._coins = coins
        self._fonte_titulo = pygame.font.SysFont(None, 80)
        self._fonte_msg = pygame.font.SysFont(None, 44)
        self._fonte_sub = pygame.font.SysFont(None, 32)
        self._fonte_stats = pygame.font.SysFont(None, 36)
        self._fonte_ph = pygame.font.SysFont(None, 28)

        # Imagem de vitória escalada para caber na área (ou None → placeholder).
        self._img: pygame.Surface | None = None
        if victory_image is not None:
            self._img = self._ajustar_imagem(victory_image)

        # Reposiciona os botões para o rodapé (abrem espaço p/ imagem + textos).
        self.botao_retry.set_relative_position((CENTRO_X - BTN_W // 2, 560))
        self.botao_menu.set_relative_position((CENTRO_X - BTN_W // 2, 630))

    def _ajustar_imagem(self, img: pygame.Surface) -> pygame.Surface:
        """Escala a imagem preservando proporção dentro de IMG_W×IMG_H."""
        iw, ih = img.get_size()
        if iw == 0 or ih == 0:
            return img  # imagem degenerada: usa como veio (evita div/0)
        fator = min(self.IMG_W / iw, self.IMG_H / ih)
        return pygame.transform.smoothscale(img, (int(iw * fator), int(ih * fator)))

    def draw(self, surface: pygame.Surface) -> None:
        """Título, imagem (ou placeholder), mensagens e estatísticas."""
        surface.fill(COLOR_HUD_BG)

        titulo = self._fonte_titulo.render(self.titulo, True, self.cor_titulo)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, 70)))

        # Imagem de vitória centralizada, ou placeholder dourado.
        area = pygame.Rect(0, 0, self.IMG_W, self.IMG_H)
        area.center = (CENTRO_X, 200)
        if self._img is not None:
            surface.blit(self._img, self._img.get_rect(center=area.center))
        else:
            pygame.draw.rect(surface, COLOR_GOLD, area, 3)
            ph = self._fonte_ph.render("[ IMAGEM DE VITÓRIA ]", True, COLOR_GOLD)
            surface.blit(ph, ph.get_rect(center=area.center))

        # Mensagem principal e submensagem (recompensa placeholder).
        msg = self._fonte_msg.render(
            "Parabéns! Você derrotou Ancelotti!", True, COR_TEXTO
        )
        surface.blit(msg, msg.get_rect(center=(CENTRO_X, 330)))
        sub = self._fonte_sub.render("Você recebe: Texas Chibi de recompensa!", True, COLOR_GOLD)
        surface.blit(sub, sub.get_rect(center=(CENTRO_X, 375)))

        # Estatísticas da partida.
        linhas = [
            f"Inimigos eliminados: {self._kills}",
            f"Moedas restantes: $ {self._coins}",
        ]
        for i, linha in enumerate(linhas):
            txt = self._fonte_stats.render(linha, True, COR_TEXTO)
            surface.blit(txt, txt.get_rect(center=(CENTRO_X, 420 + i * 40)))
