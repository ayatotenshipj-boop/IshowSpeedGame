"""Inimigos (Labubus) que caminham pelo path.

Define a classe base `Enemy` e as quatro subclasses jogáveis (Labubu1..Labubu4).
O movimento é sempre baseado em delta-time (pixels por segundo), seguindo os
waypoints do path com curvas ortogonais. Nenhum import de pygame_gui aqui.
"""

import pygame

# Tamanho do sprite do inimigo no mapa.
SPRITE_SIZE: int = 48

# Dimensões da barra de HP.
HP_BAR_WIDTH: int = 40
HP_BAR_HEIGHT: int = 5


class Enemy:
    """Classe base de inimigo. Não deve ser instanciada diretamente."""

    # Atributos de classe sobrescritos por cada subclasse.
    name: str = "Enemy"
    max_hp: int = 1
    speed: float = 0.0      # pixels por segundo
    reward: int = 0         # moedas concedidas ao morrer
    asset_name: str = ""
    damage_to_base: int = 1  # vidas que tira do jogador ao chegar ao fim

    def __init__(self, assets, waypoints: list[dict]) -> None:
        self.hp: int = self.max_hp
        self.slow_factor: float = 1.0   # 1.0 = normal, 0.5 = lento
        self.slow_timer: float = 0.0    # segundos restantes de slow

        # Posição inicial = primeiro waypoint; mira o segundo.
        self.x: float = float(waypoints[0]["x"])
        self.y: float = float(waypoints[0]["y"])
        self.waypoint_index: int = 1

        self.sprite: pygame.Surface = pygame.transform.smoothscale(
            assets.get(self.asset_name), (SPRITE_SIZE, SPRITE_SIZE)
        )

    # ------------------------------------------------------------------ #
    # Movimento
    # ------------------------------------------------------------------ #
    def update(self, dt: float, waypoints: list[dict]) -> bool:
        """Move o inimigo em direção ao próximo waypoint.

        Retorna True se o inimigo chegou ao fim do path (deve sair do mapa).
        """
        # Atualiza o efeito de slow.
        if self.slow_timer > 0.0:
            self.slow_timer -= dt
            if self.slow_timer <= 0.0:
                self.slow_timer = 0.0
                self.slow_factor = 1.0

        # Distância que pode percorrer neste frame.
        restante = self.speed * self.slow_factor * dt

        # Consome a distância segmento a segmento (evita teleporte se dt grande).
        while restante > 0.0:
            if self.waypoint_index >= len(waypoints):
                return True  # passou do último waypoint

            alvo = waypoints[self.waypoint_index]
            dx = alvo["x"] - self.x
            dy = alvo["y"] - self.y
            dist = (dx * dx + dy * dy) ** 0.5

            if dist <= restante:
                # Alcança o waypoint e sobra distância para o próximo segmento.
                self.x = float(alvo["x"])
                self.y = float(alvo["y"])
                self.waypoint_index += 1
                self._ao_passar_waypoint()  # hook (Labubu4 desacelera por curva)
                restante -= dist
            else:
                # Move parcialmente em direção ao waypoint.
                self.x += dx / dist * restante
                self.y += dy / dist * restante
                restante = 0.0

        return False

    def _ao_passar_waypoint(self) -> None:
        """Hook chamado ao alcançar um waypoint (curva). Default: nada.

        Subclasses podem reagir a cada curva (ex.: Labubu4 desacelera).
        """

    def apply_slow(self, duration: float = 2.0) -> None:
        """Ativa o efeito de lentidão (metade da velocidade) por `duration`s."""
        self.slow_factor = 0.4
        self.slow_timer = duration

    def is_dead(self) -> bool:
        """True se o HP chegou a zero."""
        return self.hp <= 0

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        """Desenha o sprite centralizado e a barra de HP (se ferido)."""
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(self.sprite, rect)

        if self.hp < self.max_hp:
            self._draw_hp_bar(surface, rect)

    def _draw_hp_bar(self, surface: pygame.Surface, sprite_rect: pygame.Rect) -> None:
        """Barra verde (HP atual) sobre fundo vermelho (HP máximo)."""
        x = int(self.x) - HP_BAR_WIDTH // 2
        y = sprite_rect.top - 4 - HP_BAR_HEIGHT
        # Fundo (HP máximo).
        pygame.draw.rect(surface, (180, 40, 40), (x, y, HP_BAR_WIDTH, HP_BAR_HEIGHT))
        # Frente (HP atual).
        frac = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(
            surface, (60, 200, 70), (x, y, int(HP_BAR_WIDTH * frac), HP_BAR_HEIGHT)
        )

    def draw_debug(self, surface: pygame.Surface, fonte: pygame.font.Font) -> None:
        """Texto pequeno com a posição abaixo do sprite (modo dev)."""
        txt = fonte.render(f"({int(self.x)},{int(self.y)})", True, (255, 255, 0))
        surface.blit(txt, (int(self.x) - txt.get_width() // 2, int(self.y) + SPRITE_SIZE // 2))


class Labubu1(Enemy):
    """Fraco e rápido."""

    name = "labubu1"
    max_hp = 60
    speed = 120.0
    reward = 15  # v1.2.1 (era 10)
    asset_name = "labubu1"


class Labubu2(Enemy):
    """Médio, equilibrado."""

    name = "labubu2"
    max_hp = 140
    speed = 80.0
    reward = 30  # v1.2.1 (era 20)
    asset_name = "labubu2"


class Labubu3(Enemy):
    """Tanque lento e resistente."""

    name = "labubu3"
    max_hp = 300
    speed = 50.0
    reward = 50  # v1.2.1 (era 35)
    asset_name = "labubu3"
    damage_to_base = 2


class Labubu4(Enemy):
    """Rápido e resistente; cansa (desacelera) após 4 curvas."""

    name = "labubu4"
    max_hp = 220
    speed = 110.0
    reward = 45  # v1.2.1 (era 30)
    asset_name = "labubu4"
    damage_to_base = 2

    def __init__(self, assets, waypoints: list[dict]) -> None:
        super().__init__(assets, waypoints)
        self.curvas: int = 0
        self.velocidade_base: float = type(self).speed

    def _ao_passar_waypoint(self) -> None:
        """A cada curva além da 4ª, perde 10% da velocidade base (piso 30%)."""
        self.curvas += 1
        if self.curvas > 4:
            reducao = (self.curvas - 4) * 0.05
            self.speed = max(
                self.velocidade_base * 0.30,
                self.velocidade_base * (1.0 - reducao),
            )


class LabubuMUI(Enemy):
    """Reforço invocado pelo Ancelotti ao tomar dano (50% mais fraco).

    Reaproveita o sprite do Labubu1 com um tint vermelho para diferenciar.
    Os stats reais são definidos pela fábrica `criar_mui` (dependem da wave).
    NÃO entra em `ENEMY_TYPES`: nunca é spawnado por onda, só pelo boss.
    """

    name = "Labubu MUI"
    max_hp = 30   # placeholder; criar_mui sobrescreve
    speed = 60.0
    reward = 8   # v1.2.1 (piso); criar_mui sobrescreve
    asset_name = "labubu1"  # reaproveita o sprite do Labubu1
    damage_to_base = 1

    def __init__(self, assets, waypoints: list[dict]) -> None:
        super().__init__(assets, waypoints)
        # Tint vermelho numa CÓPIA (não corromper o sprite cacheado no AssetManager).
        self.sprite = self.sprite.copy()
        self.sprite.fill((255, 80, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)


def criar_mui(assets, waypoints: list[dict], wave_atual: int) -> LabubuMUI:
    """Cria um Labubu MUI com 50% dos stats do Labubu de referência da wave.

    `wave_atual` é 1-based (número de exibição). Aplica o mesmo multiplicador de
    HP por wave usado nas ondas, depois reduz tudo em 50%.
    """
    if wave_atual >= 12:
        ref_hp, ref_speed, ref_reward = 220, 110, 45   # Labubu4 base (reward v1.2.1)
    elif wave_atual >= 8:
        ref_hp, ref_speed, ref_reward = 300, 50, 50    # Labubu3 base (reward v1.2.1)
    elif wave_atual >= 5:
        ref_hp, ref_speed, ref_reward = 140, 80, 30    # Labubu2 base (reward v1.2.1)
    else:
        ref_hp, ref_speed, ref_reward = 60, 120, 15    # Labubu1 base (reward v1.2.1)

    mult = 1.0 + wave_atual * 0.10
    mui = LabubuMUI(assets, waypoints)
    mui.max_hp = int(ref_hp * mult * 0.5)
    mui.hp = mui.max_hp
    mui.speed = ref_speed * 0.5
    mui.reward = max(8, int(ref_reward * 0.5))
    return mui


# Mapeia o nome usado nas ondas para a classe correspondente.
ENEMY_TYPES: dict[str, type[Enemy]] = {
    "labubu1": Labubu1,
    "labubu2": Labubu2,
    "labubu3": Labubu3,
    "labubu4": Labubu4,
}
