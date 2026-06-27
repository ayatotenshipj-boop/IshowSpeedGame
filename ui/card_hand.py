"""Mão de cartas do jogador (barra inferior).

Renderiza as cartas de Speed na HUD_RECT e mapeia cliques para índices de
carta. Camada de UI: apenas desenho e mapeamento de input — nenhuma lógica de
jogo (desconto de moedas, posicionamento e limites ficam no main/loop). O
desenho recebe a lista de torres apenas para *contar* quantas de cada tipo já
estão no campo (barra de slots) — não a modifica.
"""

import pygame

from config.settings import (
    CARD_HEIGHT,
    COLOR_CARD_BG,
    COLOR_CARD_DESC,
    COLOR_CARD_LIMIT,
    COLOR_CARD_STATS,
    COLOR_GOLD,
    COLOR_SELECTED,
    COLOR_SLOT_OFF,
    COLOR_SLOT_ON,
    COR_TEXTO,
    COR_FUNDO_HUD,
    COR_CARTA_TOPO,
    COR_BORDA_CARTA,
    COR_OVERLAY_BLOQUEADA,
    COR_TOOLTIP_FUNDO,
    COR_BUFF_IND,
    COR_SKILL_USADA,
    COR_ROXO_IND,
    HUD_RECT,
    WINDOW_WIDTH,
)
from entities.tower import TOWER_TYPES

# Sprite dentro da carta.
CARD_SPRITE_SIZE: int = 40
# Espaço horizontal entre cartas.
CARD_GAP: int = 12
# Dimensões de cada quadradinho de slot.
SLOT_SIZE: int = 8
SLOT_GAP: int = 3
# Tempo de hover (segundos) antes de exibir o tooltip da carta.
TOOLTIP_DELAY: float = 0.5


class CardHand:
    """Cartas de Speed exibidas na barra inferior."""

    def __init__(self, assets) -> None:
        self.selected: int | None = None

        # Estado de hover para o tooltip (índice e tempo acumulado sobre a carta).
        self._hover_idx: int | None = None
        self._hover_timer: float = 0.0

        # Fontes: BebasNeue (TTF) para custo/moedas, Liberation Sans Bold para nomes.
        from config.settings import FONTE_TITULO_PATH
        self._fonte_stats = pygame.font.SysFont("monospace", 11)
        self._fonte_custo = pygame.font.Font(str(FONTE_TITULO_PATH), 18)
        self._fonte_ind = pygame.font.SysFont("monospace", 13, bold=True)
        self._fonte_moedas = pygame.font.Font(str(FONTE_TITULO_PATH), 28)
        self._fonte_tip = pygame.font.SysFont("liberationsans", 18, bold=True)
        self._fonte_tip_peq = pygame.font.SysFont("monospace", 13)

        # Surfaces cacheadas — evitar alocação por frame
        # (tamanho calculado após _rects, mais abaixo)
        self._carta_surf: pygame.Surface | None = None
        self._overlay_bloqueada_surf: pygame.Surface | None = None

        # Pré-renderiza o sprite de cada carta uma única vez.
        self._sprites: list[pygame.Surface] = [
            pygame.transform.smoothscale(
                assets.get(t.asset_name), (CARD_SPRITE_SIZE, CARD_SPRITE_SIZE)
            )
            for t in TOWER_TYPES
        ]

        # Largura dinâmica para caber todas as cartas (deixa 160px à esquerda
        # para o saldo de moedas). Bloco alinhado à direita da HUD_RECT.
        n = len(TOWER_TYPES)
        card_w = (WINDOW_WIDTH - 160) // n
        largura_total = n * card_w + (n - 1) * CARD_GAP
        x0 = HUD_RECT.right - largura_total - 12
        y0 = HUD_RECT.y + (HUD_RECT.height - CARD_HEIGHT) // 2
        self._rects: list[pygame.Rect] = [
            pygame.Rect(x0 + i * (card_w + CARD_GAP), y0, card_w, CARD_HEIGHT)
            for i in range(n)
        ]

        # Inicializa surfaces cacheadas agora que _rects está definido
        if self._rects:
            card_size = self._rects[0].size
            self._carta_surf = pygame.Surface(card_size, pygame.SRCALPHA)
            self._overlay_bloqueada_surf = pygame.Surface(card_size, pygame.SRCALPHA)
            self._overlay_bloqueada_surf.fill(COR_OVERLAY_BLOQUEADA)

        # Pré-renderiza nome e descrição já AJUSTADOS para caber na carta
        # (nomes longos como "KindaHomeless Speed" transbordavam). Estático por
        # tipo: calculado uma vez, sem custo por frame.
        larg_nome = card_w - 56 - 6      # nome começa em x=56
        larg_desc = card_w - 16          # descrição começa em x=8
        self._nome_surfs: list[pygame.Surface] = [
            self._render_texto_ajustado(t.nome, larg_nome, COR_TEXTO, 22, 11, bold=True)
            for t in TOWER_TYPES
        ]
        self._desc_surfs: list[pygame.Surface | None] = [
            self._render_texto_ajustado(
                t.description, larg_desc, COLOR_CARD_DESC, 10, 8, mono=True, italic=True
            ) if t.description else None
            for t in TOWER_TYPES
        ]

    # ------------------------------------------------------------------ #
    # Texto ajustável (Bloco 4)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _render_texto_ajustado(
        texto: str,
        larg_max: int,
        cor: tuple[int, int, int],
        font_max: int,
        font_min: int,
        bold: bool = False,
        italic: bool = False,
        mono: bool = False,
    ) -> pygame.Surface:
        """Renderiza `texto` reduzindo a fonte de `font_max` a `font_min` até
        caber em `larg_max` px. Se nem no mínimo couber, trunca com reticências.
        """
        if mono:
            fam = "monospace"
        elif bold:
            fam = "liberationsans"  # Oswald bold → Liberation Sans Bold (disponível no Linux)
        else:
            fam = None
        for tam in range(font_max, font_min - 1, -1):
            fonte = pygame.font.SysFont(fam, tam, bold=bold, italic=italic)
            if fonte.size(texto)[0] <= larg_max:
                return fonte.render(texto, True, cor)
        # Não coube nem no menor tamanho: trunca caractere a caractere com "…".
        fonte = pygame.font.SysFont(fam, font_min, bold=bold, italic=italic)
        trunc = texto
        while trunc and fonte.size(trunc + "…")[0] > larg_max:
            trunc = trunc[:-1]
        return fonte.render((trunc + "…") if trunc else "…", True, cor)

    # ------------------------------------------------------------------ #
    # Seleção
    # ------------------------------------------------------------------ #
    def select(self, index: int) -> None:
        """Marca a carta `index` como selecionada."""
        self.selected = index

    def deselect(self) -> None:
        """Remove a seleção atual."""
        self.selected = None

    def handle_click(self, pos: tuple[int, int]) -> int | None:
        """Retorna o índice da carta clicada ou None se nenhuma."""
        for i, rect in enumerate(self._rects):
            if rect.collidepoint(pos):
                return i
        return None

    # ------------------------------------------------------------------ #
    # Hover / tooltip
    # ------------------------------------------------------------------ #
    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        """Acompanha o tempo de hover sobre a carta sob o cursor (tooltip).

        `mouse_pos` já vem em coordenadas de render (convertido pelo main).
        """
        idx = self.handle_click(mouse_pos)
        if idx != self._hover_idx:
            self._hover_idx = idx
            self._hover_timer = 0.0
        elif idx is not None:
            self._hover_timer += dt

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface, coins: int, towers=()) -> None:
        """Desenha a barra, o saldo e as cartas (com slots por tipo já posto)."""
        surface.fill(COR_FUNDO_HUD, HUD_RECT)

        # Saldo de moedas à esquerda das cartas.
        txt_moedas = self._fonte_moedas.render(f"$ {coins}", True, COLOR_GOLD)
        surface.blit(
            txt_moedas,
            (HUD_RECT.x + 16, HUD_RECT.y + HUD_RECT.height // 2 - txt_moedas.get_height() // 2),
        )

        for i, (rect, tipo, sprite) in enumerate(
            zip(self._rects, TOWER_TYPES, self._sprites)
        ):
            postas = [t for t in towers if type(t) is tipo]
            self._desenhar_carta(
                surface, rect, tipo, sprite, coins, len(postas), postas,
                i == self.selected, self._nome_surfs[i], self._desc_surfs[i],
            )

    def draw_tooltip(self, surface: pygame.Surface) -> None:
        """Exibe um tooltip detalhado se o cursor está sobre uma carta por >=0.5s."""
        if self._hover_idx is None or self._hover_timer < TOOLTIP_DELAY:
            return

        tipo = TOWER_TYPES[self._hover_idx]
        linhas = [
            (tipo.nome, self._fonte_tip, COLOR_GOLD),
            (f"Custo: ${tipo.cost}", self._fonte_tip_peq, COR_TEXTO),
            (f"Dano: {tipo.damage}", self._fonte_tip_peq, COLOR_CARD_STATS),
            (f"Alcance: {tipo.range_px}px", self._fonte_tip_peq, COLOR_CARD_STATS),
            (f"Cadência: {tipo.fire_rate:.1f}/s", self._fonte_tip_peq, COLOR_CARD_STATS),
            (f"Máx. no campo: {tipo.max_no_campo}", self._fonte_tip_peq, COLOR_CARD_STATS),
            (tipo.description, self._fonte_tip_peq, COLOR_CARD_DESC),
        ]
        renders = [(f.render(t, True, c), c) for t, f, c in linhas if t]
        larg = max(r.get_width() for r, _ in renders) + 20
        alt = sum(r.get_height() for r, _ in renders) + 16 + 4 * (len(renders) - 1)

        # Posiciona o tooltip acima da carta sob o cursor, dentro da tela.
        rect_carta = self._rects[self._hover_idx]
        x = min(rect_carta.centerx - larg // 2, WINDOW_WIDTH - larg - 6)
        x = max(6, x)
        y = rect_carta.top - alt - 8

        fundo = pygame.Rect(x, y, larg, alt)
        painel = pygame.Surface(fundo.size, pygame.SRCALPHA)
        painel.fill(COR_TOOLTIP_FUNDO)
        surface.blit(painel, fundo.topleft)
        pygame.draw.rect(surface, COLOR_GOLD, fundo, 1)

        cy = y + 8
        for render, _cor in renders:
            surface.blit(render, (x + 10, cy))
            cy += render.get_height() + 4

    def _desenhar_carta(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        tipo,
        sprite: pygame.Surface,
        coins: int,
        n_postas: int,
        postas: list,
        selecionada: bool,
        nome_surf: pygame.Surface,
        desc_surf: pygame.Surface | None,
    ) -> None:
        """Desenha uma carta individual na surface cacheada (para alpha)."""
        carta = self._carta_surf
        carta.fill((0, 0, 0, 0))  # limpar antes de redesenhar
        area = pygame.Rect(0, 0, rect.width, rect.height)
        no_limite = n_postas >= tipo.max_no_campo

        # Fundo oliva escuro + faixa-topo levemente mais clara (simula border-top HTML).
        carta.fill(COLOR_CARD_BG, area)
        carta.fill(COR_CARTA_TOPO, pygame.Rect(0, 0, rect.width, 2))

        # Sprite no canto superior esquerdo + nome ao lado (já ajustado p/ caber).
        carta.blit(sprite, (8, 8))
        carta.blit(nome_surf, (56, 14))

        # Stats em duas linhas (monospace).
        l1 = f"Dano:{tipo.damage}  Alc:{tipo.range_px}px"
        l2 = f"Cad:{tipo.fire_rate:.1f}/s  Custo:${tipo.cost}"
        carta.blit(self._fonte_stats.render(l1, True, COLOR_CARD_STATS), (8, 47))
        carta.blit(self._fonte_stats.render(l2, True, COLOR_CARD_STATS), (8, 59))

        # Descrição curta (itálico, já ajustada p/ caber).
        if desc_surf is not None:
            carta.blit(desc_surf, (8, 72))

        # Barra de slots (quantas torres deste tipo já estão no campo).
        slots_y = rect.height - SLOT_SIZE - 3
        for s in range(tipo.max_no_campo):
            cor = COLOR_SLOT_ON if s < n_postas else COLOR_SLOT_OFF
            carta.fill(cor, pygame.Rect(8 + s * (SLOT_SIZE + SLOT_GAP), slots_y, SLOT_SIZE, SLOT_SIZE))
        # Contador textual à direita dos slots.
        cont = self._fonte_stats.render(f"{n_postas}/{tipo.max_no_campo}", True, COLOR_CARD_STATS)
        carta.blit(cont, (8 + tipo.max_no_campo * (SLOT_SIZE + SLOT_GAP) + 6, slots_y - 2))

        # Indicadores de buff/habilidade (dormentes até Speed6/7 existirem).
        self._desenhar_indicadores(carta, postas, rect)

        # Custo dourado no canto superior direito.
        txt_custo = self._fonte_custo.render(f"${tipo.cost}", True, COLOR_GOLD)
        carta.blit(txt_custo, (rect.width - txt_custo.get_width() - 6, 2))

        # Borda: dourada se selecionada, vermelha se no limite, oliva-escuro senão.
        if selecionada:
            pygame.draw.rect(carta, COLOR_SELECTED, area, 2)
        elif no_limite:
            pygame.draw.rect(carta, COLOR_CARD_LIMIT, area, 2)
        else:
            pygame.draw.rect(carta, COR_BORDA_CARTA, area, 1)

        surface.blit(carta, rect.topleft)

        # Overlay escuro se inacessível (sem moedas ou no limite) — surface cacheada.
        if coins < tipo.cost or no_limite:
            surface.blit(self._overlay_bloqueada_surf, rect.topleft)

    def _desenhar_indicadores(self, carta: pygame.Surface, postas: list, rect: pygame.Rect) -> None:
        """Indicadores defensivos de buff (`[B]`) e habilidade (`[SKILL]`/`[USADA]`).

        Guardados por `getattr`: só aparecem quando as torres tiverem esses
        atributos (Speed6/Speed7, ainda não implementadas).
        """
        piscando = (pygame.time.get_ticks() // 400) % 2 == 0

        if any(getattr(t, "buff_active", False) for t in postas) and piscando:
            buff = self._fonte_ind.render("[B]", True, COR_BUFF_IND)
            carta.blit(buff, (rect.width - buff.get_width() - 6, rect.height - 22))

        # ability_used: None=sem habilidade; False=disponível; True=já usada.
        estados = [getattr(t, "ability_used", None) for t in postas]
        if any(e is False for e in estados):
            if piscando:
                sk = self._fonte_ind.render("[SKILL]", True, COR_ROXO_IND)
                carta.blit(sk, (4, rect.height - 22))
        elif any(e is True for e in estados):
            sk = self._fonte_ind.render("[USADA]", True, COR_SKILL_USADA)
            carta.blit(sk, (4, rect.height - 22))
