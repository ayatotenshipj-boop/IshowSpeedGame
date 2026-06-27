"""Cena de introdução em diálogo, estilo Undertale.

Camada de UI pura: apenas renderização e tratamento de input — nenhuma lógica
de jogo. Mostra uma sequência de falas entre personagens, com efeito de máquina
de escrever (typewriter), antes do menu principal. O `main` cria a cena, chama
`update`/`handle_event`/`draw` enquanto estiver em `GameScreen.INTRO` e, ao
final (`handle_event` retorna True), transiciona para o menu.

Segue o mesmo protocolo das telas de menu (`handle_event`, `draw`, `destroy`)
para ocupar o mesmo slot `current_screen` do loop principal.
"""

import pygame

from config.settings import (
    COLOR_GOLD, WINDOW_HEIGHT, WINDOW_WIDTH,
    COR_TEXTO, COR_BOSS_ALERTA, COR_ROXO_IND,
    COR_FUNDO_TELA, COR_INTRO_ESCURO, COR_DIALOGO_FUNDO, COR_HINT_DIALOGO,
)

# Tamanho dos retratos dos personagens.
SPRITE_SIZE: int = 300
# Duração do fade-out de saída da intro para o menu (segundos).
FADE_OUT_DURATION: float = 0.6
# Margens e dimensões da caixa de diálogo.
BOX_MARGIN: int = 40
BOX_HEIGHT: int = 180
BOX_BOTTOM_GAP: int = 60
# Velocidade do typewriter (caracteres por segundo) e largura de quebra.
CHARS_PER_SEC: float = 40.0
WRAP_CHARS: int = 60

# Configuração de cada personagem: chave de sprite (qualificada), lado, cor, nome.
PERSONAGENS: dict[str, dict] = {
    "speed": {"sprite": "dialogs/speed-removebg-preview", "lado": "direita", "cor": COLOR_GOLD, "nome": "Speed"},
    "ancelotti": {"sprite": "dialogs/ancelotti-removebg-preview", "lado": "esquerda", "cor": COR_BOSS_ALERTA, "nome": "Ancelotti"},
    "labubu": {"sprite": "labubus/labubu1", "lado": "esquerda", "cor": COR_ROXO_IND, "nome": "Labubu"},
}

# Sequência de falas (textos placeholder — o usuário preenche depois).
DIALOG_SEQUENCE: list[dict] = [
    {"speaker": "speed", "text": "[Ancelotti! Seu racista de merda, escala o Endrick!!]"},
    {"speaker": "ancelotti", "text": "[Não vou escalar ele, eu não quero]"},
    {"speaker": "speed", "text": "[Você é um idiota, Ancelotti!]"},
    {"speaker": "speed", "text": "[Por que não quer escalar o Endrick?]"},
    {"speaker": "speed", "text": "[Ele é um dos melhores jogadores que temos e você não quer escalar ele?]"},
    {"speaker": "ancelotti", "text": "[Não insiste em discutir comigo speed, eu não quero escalar o Endrick]"},
    {"speaker": "ancelotti", "text": "[Se você não parar de me encher o saco, vai lidar com uma surpresa]"},
    {"speaker": "speed", "text": "[Eu não tenho medo de você, seu racista de merda!]"},
    {"speaker": "labubu", "text": "[Labubu Labubuu! *Labubu aparece do nada*]"},
    {"speaker": "speed", "text": "[Há, você acha que pode me intimidar, seu idiota? eu vou te dar uma surra]"},
    {"speaker": "ancelotti", "text": "[Não espere que vai ser facil, isso não vai fazer o endrick ser escalado]"},
    {"speaker": "speed", "text": "[Seu racista de merda, você tá fudido!]"},
]


def _quebrar_texto(texto: str, largura: int) -> list[str]:
    """Word wrap simples: quebra `texto` em linhas de até `largura` caracteres."""
    linhas: list[str] = []
    atual = ""
    for palavra in texto.split(" "):
        candidato = palavra if not atual else f"{atual} {palavra}"
        if len(candidato) > largura and atual:
            linhas.append(atual)
            atual = palavra
        else:
            atual = candidato
    if atual:
        linhas.append(atual)
    return linhas


class IntroScene:
    """Cena de diálogo exibida antes do menu principal."""

    def __init__(self, asset_manager) -> None:
        self.dialog_index: int = 0     # fala atual
        self.char_index: int = 0       # caracteres revelados da fala atual
        self.char_timer: float = 0.0   # acumulador do typewriter
        self.chars_per_sec: float = CHARS_PER_SEC
        self.complete: bool = False    # cena terminou (fade-out concluído)
        self._finishing: bool = False  # iniciou o fade-out de saída
        self._fade_timer: float = 0.0  # progresso do fade-out

        # Fontes (monospace para o efeito retro).
        self._fonte_nome = pygame.font.SysFont("monospace", 24, bold=True)
        self._fonte_texto = pygame.font.SysFont("monospace", 18)
        self._fonte_hint = pygame.font.SysFont("monospace", 16)
        # Surfaces cacheadas
        self._escuro_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self._escuro_surf.fill(COR_INTRO_ESCURO)
        self._fade_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)

        # Fundo dinâmico: mapa do jogo escurecido (sensação de "partida prestes
        # a começar"). Ausência do asset cai para fundo preto simples.
        self._bg: pygame.Surface | None = None
        try:
            self._bg = pygame.transform.smoothscale(
                asset_manager.get("mapa"), (WINDOW_WIDTH, WINDOW_HEIGHT)
            )
        except KeyError:
            self._bg = None

        # Pré-carrega e escala os retratos uma única vez (load-once via AssetManager).
        self._sprites: dict[str, pygame.Surface] = {}
        for chave, cfg in PERSONAGENS.items():
            try:
                bruto = asset_manager.get(cfg["sprite"])
                self._sprites[chave] = pygame.transform.smoothscale(
                    bruto, (SPRITE_SIZE, SPRITE_SIZE)
                )
            except KeyError:
                # Sprite ausente: a cena segue sem o retrato desse personagem.
                self._sprites[chave] = None

    # ------------------------------------------------------------------ #
    # Estado / consultas
    # ------------------------------------------------------------------ #
    def _fala_atual(self) -> dict:
        return DIALOG_SEQUENCE[self.dialog_index]

    def _texto_completo(self) -> bool:
        """True quando todos os caracteres da fala atual já apareceram."""
        return self.char_index >= len(self._fala_atual()["text"])

    # ------------------------------------------------------------------ #
    # Atualização (typewriter)
    # ------------------------------------------------------------------ #
    def update(self, dt: float) -> None:
        """Avança o typewriter e, ao finalizar, o fade-out de saída."""
        # Fade-out de saída: ao completar, marca a cena como concluída.
        if self._finishing:
            self._fade_timer += dt
            if self._fade_timer >= FADE_OUT_DURATION:
                self.complete = True
            return

        if self._texto_completo():
            return
        self.char_timer += dt
        intervalo = 1.0 / self.chars_per_sec
        total = len(self._fala_atual()["text"])
        while self.char_timer >= intervalo and self.char_index < total:
            self.char_index += 1
            self.char_timer -= intervalo

    # ------------------------------------------------------------------ #
    # Input
    # ------------------------------------------------------------------ #
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Trata input; retorna True quando a cena deve terminar.

        ENTER/SPACE: revela tudo se ainda digitando; senão avança para a
        próxima fala (ou termina, se era a última). ESCAPE: pula a cena toda.
        """
        if event.type != pygame.KEYDOWN or self._finishing:
            return False

        if event.key == pygame.K_ESCAPE:
            self._finishing = True  # pula a cena: inicia o fade-out
            return False

        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
            if not self._texto_completo():
                # Revela toda a fala imediatamente.
                self.char_index = len(self._fala_atual()["text"])
            elif self.dialog_index + 1 < len(DIALOG_SEQUENCE):
                # Avança para a próxima fala.
                self.dialog_index += 1
                self.char_index = 0
                self.char_timer = 0.0
            else:
                # Última fala concluída: inicia o fade-out de saída.
                self._finishing = True
        return False

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        """Desenha fundo dinâmico, retratos, caixa de diálogo, texto e dicas."""
        # Fundo: mapa escurecido (surface cacheada) ou preto se ausente.
        if self._bg is not None:
            surface.blit(self._bg, (0, 0))
            surface.blit(self._escuro_surf, (0, 0))
        else:
            surface.fill(COR_FUNDO_TELA)

        fala = self._fala_atual()
        speaker = fala["speaker"]
        self._desenhar_retratos(surface, speaker)
        self._desenhar_caixa(surface, speaker, fala["text"])

        # Fade-out de saída (preto crescente) — Surface cacheada, fill por frame.
        if self._finishing:
            alpha = int(255 * min(1.0, self._fade_timer / FADE_OUT_DURATION))
            self._fade_surf.fill((0, 0, 0, alpha))
            surface.blit(self._fade_surf, (0, 0))

    def _desenhar_retratos(self, surface: pygame.Surface, falante: str) -> None:
        """Desenha dois retratos (esquerda/direita); o falante em destaque.

        Direita: sempre o Speed. Esquerda: Ancelotti, ou Labubu quando é ele
        quem fala. O personagem que não fala fica escurecido (alpha 80).
        """
        topo_y = 120
        x_esq = 60
        x_dir = WINDOW_WIDTH - 60 - SPRITE_SIZE
        esquerda = "labubu" if falante == "labubu" else "ancelotti"
        for chave, x in (("speed", x_dir), (esquerda, x_esq)):
            sprite = self._sprites.get(chave)
            if sprite is None:
                continue
            sprite = sprite.copy()
            if chave != falante:
                sprite.set_alpha(80)  # quem não fala fica escurecido
            surface.blit(sprite, (x, topo_y))

    def _desenhar_caixa(
        self, surface: pygame.Surface, falante: str, texto: str
    ) -> None:
        """Caixa de diálogo com nome, texto revelado, seta e dicas."""
        cfg = PERSONAGENS[falante]
        box = pygame.Rect(
            BOX_MARGIN,
            WINDOW_HEIGHT - BOX_BOTTOM_GAP - BOX_HEIGHT,
            WINDOW_WIDTH - 2 * BOX_MARGIN,
            BOX_HEIGHT,
        )
        pygame.draw.rect(surface, COR_DIALOGO_FUNDO, box)
        pygame.draw.rect(surface, COR_TEXTO, box, 2)

        # Nome do personagem (cor própria).
        nome = self._fonte_nome.render(cfg["nome"], True, cfg["cor"])
        surface.blit(nome, (box.x + 20, box.y + 14))

        # Texto revelado (typewriter) com quebra de linha automática.
        visivel = texto[: self.char_index]
        y = box.y + 56
        for linha in _quebrar_texto(visivel, WRAP_CHARS):
            render = self._fonte_texto.render(linha, True, COR_TEXTO)
            surface.blit(render, (box.x + 20, y))
            y += 26

        # Seta piscante quando a fala terminou de aparecer.
        if self._texto_completo() and (pygame.time.get_ticks() // 400) % 2 == 0:
            seta = self._fonte_nome.render("v", True, COR_TEXTO)
            surface.blit(seta, (box.right - 36, box.bottom - 36))

        # Dica de controles no canto inferior direito da tela.
        hint = self._fonte_hint.render(
            "ENTER: próximo | ESC: pular", True, COR_HINT_DIALOGO
        )
        surface.blit(hint, (WINDOW_WIDTH - hint.get_width() - 20, WINDOW_HEIGHT - 28))

    def destroy(self) -> None:
        """Sem elementos pygame_gui para remover (protocolo compartilhado)."""
        return
