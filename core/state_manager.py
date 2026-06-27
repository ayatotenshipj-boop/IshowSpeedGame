"""Máquina de estados de telas do jogo.

Controla qual tela está ativa: menu, jogo, pausa, game over ou vitória.
Simples e direta — sem padrão Observer nem eventos customizados.
"""

from enum import Enum, auto


class GameScreen(Enum):
    """Telas possíveis do jogo."""

    INTRO = auto()      # cena de diálogo antes do menu
    MENU = auto()
    SELECAO_MODO = auto()  # seleção de dificuldade (após JOGAR, antes da intro)
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    NOME_VITORIA = auto()  # pede o nome do jogador antes da tela de vitória
    VICTORY = auto()


class StateManager:
    """Guarda a tela atual e faz as transições."""

    def __init__(self) -> None:
        # O jogo começa no MENU; a intro é exibida após clicar em JOGAR.
        self.current: GameScreen = GameScreen.MENU

    def transition(self, new_state: GameScreen) -> None:
        """Troca para `new_state`."""
        self.current = new_state

    def is_intro(self) -> bool:
        """True se está na cena de introdução."""
        return self.current == GameScreen.INTRO

    def is_playing(self) -> bool:
        """True se está na tela de jogo."""
        return self.current == GameScreen.PLAYING

    def is_menu(self) -> bool:
        """True se está no menu principal."""
        return self.current == GameScreen.MENU
