"""Gerência de áudio do jogo (música de fundo e cues de habilidade).

Subsistema persistente: vive durante toda a execução (intro, menu, jogo, pausa)
e sobrevive a reinícios de partida — por isso o estado de música NÃO mora no
`GameState` (que é recriado a cada partida). Responsável por:

- iniciar a música de fundo (`sound.mp3`) com fade-in gradual;
- tocar o cue `killthatboy.mp3` SOBREPOSTO (canal de efeitos próprio), sem
  interromper a música de fundo, cortando-o após 1s;
- fazer crossfade da música atual para `suspensemusic.mp3` (fade-out de uma e
  fade-in da outra ao longo de N segundos);
- tolerar ausência de arquivos e mixer indisponível (headless) sem quebrar.

Todos os caminhos via `pathlib`; cada carregamento é precedido de
`Path.exists()`. Mensagens em PT-BR.
"""

import logging
from pathlib import Path

import pygame

from config.settings import (
    AUDIO_DIR,
    KILLTHATBOY_DURATION,
    MUSIC_FADE_DURATION,
    SOUNDS_DIR,
)

logger = logging.getLogger(__name__)

# Arquivos de áudio (via pathlib, nunca hardcoded absoluto).
MUSICA_FUNDO: Path = SOUNDS_DIR / "sound.mp3"
CUE_KILLTHATBOY: Path = AUDIO_DIR / "killthatboy.mp3"
MUSICA_SUSPENSE: Path = AUDIO_DIR / "suspensemusic.mp3"

# Duração do crossfade para a música de suspense (segundos).
SUSPENSE_CROSSFADE: float = 3.0


class AudioManager:
    """Controla a música de fundo e os cues de habilidade do jogo."""

    def __init__(self) -> None:
        # Inicializa o mixer; em ambiente sem áudio (headless) apenas registra.
        self._disponivel: bool = False
        try:
            pygame.mixer.init()
            self._disponivel = True
        except pygame.error as erro:
            logger.warning("Áudio indisponível (mixer não inicializou): %s", erro)

        # Estado do fade-in da música de fundo (mixer.music).
        self._fade_in: bool = False
        self._volume: float = 0.0
        # Volume-alvo definido pelo jogador (teto do fade-in). 1.0 = máximo.
        # O botão "Diminuir Música" nas Configurações reduz este valor.
        self._music_volume: float = 1.0

        # Cue killthatboy: Sound em canal próprio (sobreposto à música).
        self._sfx_killthatboy: pygame.mixer.Sound | None = self._carregar_sound(
            CUE_KILLTHATBOY
        )
        self._kill_channel: pygame.mixer.Channel | None = None
        self._kill_timer: float = 0.0

        # Crossfade para música de suspense: Sound em canal dedicado.
        self._sfx_suspense: pygame.mixer.Sound | None = self._carregar_sound(
            MUSICA_SUSPENSE
        )
        self._cross_channel: pygame.mixer.Channel | None = None
        self._cross_active: bool = False
        self._cross_timer: float = 0.0
        self._cross_dur: float = 0.0

    # ------------------------------------------------------------------ #
    # Música de fundo
    # ------------------------------------------------------------------ #
    def iniciar_fundo(self) -> None:
        """Inicia `sound.mp3` em loop com volume 0 (fade-in cuida do resto)."""
        if not self._carregar_musica(MUSICA_FUNDO):
            return
        pygame.mixer.music.set_volume(0.0)
        pygame.mixer.music.play(-1)
        self._fade_in = True
        self._volume = 0.0

    def parar(self) -> None:
        """Para música de fundo, cue killthatboy e o crossfade de suspense."""
        self._fade_in = False
        self._kill_timer = 0.0
        self._cross_active = False
        self._cross_timer = 0.0
        if not self._disponivel:
            return
        pygame.mixer.music.stop()
        if self._kill_channel is not None:
            self._kill_channel.stop()
            self._kill_channel = None
        if self._cross_channel is not None:
            self._cross_channel.stop()
            self._cross_channel = None

    # ------------------------------------------------------------------ #
    # Cue de habilidade (Speed7)
    # ------------------------------------------------------------------ #
    def ativar_killthatboy(self) -> None:
        """Toca `killthatboy.mp3` SOBREPOSTO (canal próprio), cortado em 1s.

        Não mexe na música de fundo (`mixer.music`): toca como efeito sonoro
        num canal separado e é interrompido após `KILLTHATBOY_DURATION`.
        """
        if not self._disponivel or self._sfx_killthatboy is None:
            return
        self._kill_channel = self._sfx_killthatboy.play()
        if self._kill_channel is not None:
            self._kill_channel.set_volume(1.0)
        self._kill_timer = KILLTHATBOY_DURATION

    def ativar_suspense(self) -> None:
        """Atalho: crossfade da música atual para a música de suspense."""
        self.crossfade_to(MUSICA_SUSPENSE, SUSPENSE_CROSSFADE)

    def tocar_suspense_once(self) -> float:
        """Pausa a música de fundo e toca o suspense UMA vez (sem loop).

        Retorna a duração do suspense em segundos (0.0 se indisponível). A música
        de fundo é PAUSADA (não parada) para retomar de onde parou em
        `encerrar_suspense`.
        """
        if not self._disponivel or self._sfx_suspense is None:
            return 0.0
        # Pausa a música de fundo (mantém a posição para retomar depois).
        pygame.mixer.music.pause()
        # Toca o suspense uma única vez num canal dedicado.
        if self._cross_channel is not None:
            self._cross_channel.stop()
        self._cross_active = False  # não usar o fade-in de crossfade
        self._cross_channel = self._sfx_suspense.play(loops=0)
        if self._cross_channel is not None:
            self._cross_channel.set_volume(self._music_volume)
        return self._sfx_suspense.get_length()

    def encerrar_suspense(self) -> None:
        """Para o suspense (se ainda tocar) e RETOMA a música de fundo do ponto."""
        if not self._disponivel:
            return
        if self._cross_channel is not None:
            self._cross_channel.stop()
            self._cross_channel = None
        self._cross_active = False
        pygame.mixer.music.unpause()

    # ------------------------------------------------------------------ #
    # Volume da música (Configurações)
    # ------------------------------------------------------------------ #
    def abaixar_volume(self, passo: float = 0.2) -> float:
        """Reduz o volume-alvo da música em `passo` (mín. 0.0). Retorna o novo.

        Aplica imediatamente à música de fundo e ao canal de crossfade, e baixa
        o volume corrente do fade-in se ele já passou do novo teto.
        """
        self._music_volume = max(0.0, self._music_volume - passo)
        self._volume = min(self._volume, self._music_volume)
        if self._disponivel:
            pygame.mixer.music.set_volume(self._music_volume)
            if self._cross_channel is not None and not self._cross_active:
                self._cross_channel.set_volume(self._music_volume)
        return self._music_volume

    def set_volume(self, valor: float) -> None:
        """Define o volume-alvo da música (0.0–1.0) e aplica imediatamente.

        Usado pelo slider das Configurações. Encerra o fade-in (o jogador
        escolheu um valor explícito) e ajusta a música de fundo e o canal de
        crossfade ativo.
        """
        self._music_volume = max(0.0, min(1.0, valor))
        self._volume = self._music_volume  # encerra o fade-in no valor escolhido
        if self._disponivel:
            pygame.mixer.music.set_volume(self._music_volume)
            if self._cross_channel is not None and not self._cross_active:
                self._cross_channel.set_volume(self._music_volume)

    @property
    def volume_musica(self) -> float:
        """Volume-alvo atual da música (0.0–1.0)."""
        return self._music_volume

    # ------------------------------------------------------------------ #
    # Crossfade de música
    # ------------------------------------------------------------------ #
    def crossfade_to(self, novo_arquivo: Path, duracao_segundos: float) -> None:
        """Faz crossfade da música de fundo atual para `novo_arquivo`.

        Inicia o fade-out da música atual (`mixer.music.fadeout`) e, ao mesmo
        tempo, toca o novo arquivo num canal dedicado com volume 0 subindo
        gradualmente até 1.0 ao longo de `duracao_segundos` (gerido no update).
        """
        if not self._disponivel:
            return

        # Reaproveita o suspense pré-carregado; caso contrário, carrega na hora.
        if novo_arquivo == MUSICA_SUSPENSE and self._sfx_suspense is not None:
            som = self._sfx_suspense
        else:
            som = self._carregar_sound(novo_arquivo)
        if som is None:
            return

        # Fade-out da música de fundo atual (não bloqueante).
        self._fade_in = False
        pygame.mixer.music.fadeout(int(duracao_segundos * 1000))

        # Inicia a nova música em loop, volume 0, e arma a subida gradual.
        if self._cross_channel is not None:
            self._cross_channel.stop()
        self._cross_channel = som.play(loops=-1)
        if self._cross_channel is not None:
            self._cross_channel.set_volume(0.0)
        self._cross_active = True
        self._cross_timer = 0.0
        self._cross_dur = max(0.01, duracao_segundos)

    # ------------------------------------------------------------------ #
    # Atualização por frame
    # ------------------------------------------------------------------ #
    def update(self, dt: float) -> None:
        """Avança fade-in da música, corte do killthatboy e o crossfade."""
        if not self._disponivel:
            return

        # Fade-in gradual do volume da música de fundo, limitado ao teto
        # escolhido pelo jogador (_music_volume).
        if self._fade_in:
            self._volume += dt / MUSIC_FADE_DURATION
            if self._volume >= self._music_volume:
                self._volume = self._music_volume
                self._fade_in = False
            pygame.mixer.music.set_volume(self._volume)

        # Corte do killthatboy após 1s (não afeta a música de fundo).
        if self._kill_timer > 0.0:
            self._kill_timer -= dt
            if self._kill_timer <= 0.0:
                self._kill_timer = 0.0
                if self._kill_channel is not None:
                    self._kill_channel.stop()
                    self._kill_channel = None

        # Crossfade: sobe o volume da nova música ao longo de `_cross_dur`.
        if self._cross_active and self._cross_channel is not None:
            self._cross_timer += dt
            frac = min(1.0, self._cross_timer / self._cross_dur)
            self._cross_channel.set_volume(frac)
            if frac >= 1.0:
                self._cross_active = False

    # ------------------------------------------------------------------ #
    # Auxiliares
    # ------------------------------------------------------------------ #
    def _carregar_musica(self, caminho: Path) -> bool:
        """Carrega um arquivo no canal `mixer.music`; False (com aviso) se faltar."""
        if not self._disponivel:
            return False
        if not caminho.exists():
            logger.warning("Arquivo de áudio não encontrado: %s", caminho)
            return False
        try:
            pygame.mixer.music.load(str(caminho))
        except pygame.error as erro:
            logger.warning("Falha ao carregar música '%s': %s", caminho, erro)
            return False
        return True

    def _carregar_sound(self, caminho: Path) -> "pygame.mixer.Sound | None":
        """Carrega um `Sound` (canal de efeitos); None (com aviso) se faltar."""
        if not self._disponivel:
            return None
        if not caminho.exists():
            logger.warning("Arquivo de áudio não encontrado: %s", caminho)
            return None
        try:
            return pygame.mixer.Sound(str(caminho))
        except pygame.error as erro:
            logger.warning("Falha ao carregar efeito '%s': %s", caminho, erro)
            return None
