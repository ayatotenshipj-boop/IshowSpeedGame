"""Torres (Speeds) que o jogador posiciona no campo.

Define a classe base `Tower` e as subclasses jogáveis (Speed1..Speed5, Speed7).
Os atributos de jogo (custo, dano, alcance, cadência, limite no campo) são
atributos de classe; cada instância carrega seu sprite uma vez via AssetManager
e guarda a célula onde foi posicionada. Nenhum import de pygame_gui aqui
(regra de arquitetura).

Os nomes exibidos (`nome`) seguem o personagem (Shake It Speed, etc.). Speed5
incorpora o antigo Speed6: é uma carta única que entra em "modo buff" (sprite
speed6, dano dobrado por 5s, cooldown 15s) ao ser ativada na torre posicionada.
"""

import pygame

from config.settings import CELL_SIZE, MAX_PER_TYPE
from entities.enemy import Enemy
from entities.projectile import Projectile

# Tamanho do sprite da torre no mapa (célula menos um padding de 8px).
SPRITE_SIZE: int = CELL_SIZE - 8  # 56×56

# Sistema de upgrade.
MAX_LEVEL: int = 3
UPGRADE_DANO: float = 0.30       # +30% de dano por nível
UPGRADE_ALCANCE: float = 0.10    # +10% de alcance por nível
UPGRADE_CADENCIA: float = 0.10   # +10% de cadência por nível
UPGRADE_CUSTO_BASE: float = 0.60  # custo do 1º upgrade = 60% do custo base
UPGRADE_CUSTO_ESCALA: float = 1.5  # cresce 1.5× por nível
VENDA_REEMBOLSO: float = 0.60    # devolve 60% do total investido


class Tower:
    """Classe base de torre. Não deve ser instanciada diretamente."""

    # Atributos de classe sobrescritos por cada subclasse.
    nome: str = "Tower"
    cost: int = 0
    damage: int = 0
    range_px: int = 0
    fire_rate: float = 0.0  # tiros por segundo
    slow: bool = False      # se reduz a velocidade do inimigo
    asset_name: str = ""
    description: str = ""    # texto curto exibido na carta
    cell_radius: int = 0     # raio de ocupação em células (0 = só a própria)
    # Máximo desta torre no campo. Default = limite global; subclasses podem
    # restringir (ex.: Speed4/Speed7 = 1).
    max_no_campo: int = MAX_PER_TYPE

    def __init__(self, assets, x: float, y: float, cell_x: int, cell_y: int) -> None:
        # Posição exata em pixels de tela (posicionamento livre, sem snap ao grid).
        self.x: float = float(x)
        self.y: float = float(y)
        # Célula que contém o pixel central (usada só pelo grid de ocupação).
        self.cell_x: int = cell_x
        self.cell_y: int = cell_y
        # Estado de combate.
        self.fire_timer: float = 0.0       # tempo até poder disparar de novo
        self.target: Enemy | None = None   # inimigo atualmente mirado
        # Estado de upgrade. Os status efetivos viram atributos de instância
        # (partem do valor-base de classe e crescem com o nível).
        self.level: int = 1
        self.invested: int = type(self).cost  # total gasto (base + upgrades)
        self.damage: int = type(self).damage
        self.range_px: int = type(self).range_px
        self.fire_rate: float = type(self).fire_rate
        # Sprite escalado para uma célula (56×56). Mesmo torres com cell_radius>0
        # (Speed3/Speed7, que bloqueiam área maior no grid) usam o sprite de uma
        # célula — manter proporcional ao resto evita torres visualmente enormes.
        self.sprite: pygame.Surface = pygame.transform.smoothscale(
            assets.get(self.asset_name), (SPRITE_SIZE, SPRITE_SIZE)
        )

    # ------------------------------------------------------------------ #
    # Combate
    # ------------------------------------------------------------------ #
    def update(self, dt: float, enemies: list[Enemy]) -> Projectile | None:
        """Avança a cadência e dispara no inimigo mais avançado no alcance.

        Retorna o Projectile criado neste frame, ou None.
        """
        if self.fire_timer > 0.0:
            self.fire_timer -= dt

        if self.fire_timer <= 0.0:
            self.target = self._find_target(enemies)
            if self.target is not None:
                cx, cy = self.centro_pixel()
                projetil = Projectile(cx, cy, self.target, self.effective_damage(), self.slow)
                # fire_rate em tiros/segundo → intervalo = 1/fire_rate.
                self.fire_timer = 1.0 / self.fire_rate
                return projetil
        return None

    def _find_target(self, enemies: list[Enemy]) -> Enemy | None:
        """Inimigo mais avançado no path dentro do alcance.

        Empate de waypoint_index → o mais próximo do próximo waypoint
        (menor distância da torre, como aproximação simples e estável).
        """
        cx, cy = self.centro_pixel()
        alcance2 = self.range_px * self.range_px
        melhor: Enemy | None = None
        for inimigo in enemies:
            dx = inimigo.x - cx
            dy = inimigo.y - cy
            dist2 = dx * dx + dy * dy
            if dist2 > alcance2:
                continue
            if (
                melhor is None
                or inimigo.waypoint_index > melhor.waypoint_index
                or (
                    inimigo.waypoint_index == melhor.waypoint_index
                    and dist2 < (melhor.x - cx) ** 2 + (melhor.y - cy) ** 2
                )
            ):
                melhor = inimigo
        return melhor

    # ------------------------------------------------------------------ #
    # Posição
    # ------------------------------------------------------------------ #
    def centro_pixel(self) -> tuple[int, int]:
        """Centro da torre, em pixels de tela (posição exata do clique)."""
        return int(self.x), int(self.y)

    # ------------------------------------------------------------------ #
    # Combate (dano efetivo) e upgrade/venda
    # ------------------------------------------------------------------ #
    def effective_damage(self) -> int:
        """Dano realmente aplicado no disparo (subclasses podem modificar)."""
        return self.damage

    def can_upgrade(self) -> bool:
        """True se a torre ainda pode subir de nível."""
        return self.level < MAX_LEVEL

    def upgrade_cost(self) -> int:
        """Custo do próximo upgrade (60% do base, crescendo 1.5× por nível)."""
        return round(
            type(self).cost * UPGRADE_CUSTO_BASE * (UPGRADE_CUSTO_ESCALA ** (self.level - 1))
        )

    def _stats_no_nivel(self, nivel: int) -> tuple[int, int, float]:
        """Status (dano, alcance, cadência) num dado nível, a partir do base."""
        fator = nivel - 1
        bd, br, bf = type(self).damage, type(self).range_px, type(self).fire_rate
        return (
            round(bd * (1 + UPGRADE_DANO * fator)),
            round(br * (1 + UPGRADE_ALCANCE * fator)),
            bf * (1 + UPGRADE_CADENCIA * fator),
        )

    def next_stats(self) -> tuple[int, int, float] | None:
        """Status do próximo nível (None se já no máximo)."""
        if not self.can_upgrade():
            return None
        return self._stats_no_nivel(self.level + 1)

    def apply_upgrade(self, custo: int) -> None:
        """Sobe um nível, recalcula os status e soma o custo ao investido."""
        if not self.can_upgrade():
            return
        self.level += 1
        self.damage, self.range_px, self.fire_rate = self._stats_no_nivel(self.level)
        self.invested += custo

    def sell_refund(self) -> int:
        """Moedas devolvidas ao vender (60% do total investido)."""
        return round(self.invested * VENDA_REEMBOLSO)

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #
    def draw(self, surface: pygame.Surface) -> None:
        """Desenha o sprite centralizado na célula."""
        rect = self.sprite.get_rect(center=self.centro_pixel())
        surface.blit(self.sprite, rect)

    def draw_range(self, surface: pygame.Surface) -> None:
        """Desenha o círculo de alcance semi-transparente (apenas modo dev)."""
        centro = self.centro_pixel()
        raio = self.range_px
        overlay = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (255, 255, 255, 40), (raio, raio), raio)
        pygame.draw.circle(overlay, (255, 255, 255, 120), (raio, raio), raio, 2)
        surface.blit(overlay, (centro[0] - raio, centro[1] - raio))


class Speed1(Tower):
    """Shake It Speed — early game, barato, cadência alta."""

    nome = "Shake It Speed"
    cost = 50
    damage = 9        # já com buff v1.2.1 (+5%: 8.4 -> 8)
    range_px = 120
    fire_rate = 2.10  # já com buff v1.2.1 (+5%); ponto forte: cadência alta
    slow = False
    asset_name = "speed1"
    description = "Cadência alta. Fraco contra tanques."


class Speed2(Tower):
    """Suprised Speed — early/mid, maior alcance."""

    nome = "Suprised Speed"
    cost = 75
    damage = 14      # já com buff v1.2.1 (+5%: 10.5 -> 11)
    range_px = 220   # ponto forte: maior alcance
    fire_rate = 1.15  # já com buff v1.2.1 (+5%)
    slow = False
    asset_name = "speed2"
    description = "Alcance amplo. Cadência lenta."


class Speed3(Tower):
    """SayWallahi Speed — sniper de dano massivo, alcance curto."""

    nome = "SayWallahi Speed"
    cost = 110
    damage = 47   # já com buff v1.2.1 (+5%: 47.25 -> 47); ponto forte: dano altíssimo
    range_px = 135
    fire_rate = 0.55  # já com buff v1.2.1 (+5%)
    slow = False
    asset_name = "speed3"
    description = "Dano massivo. Alcance curto e lento."
    cell_radius = 1  # torre grande: bloqueia área 3×3


class Speed4(Tower):
    """KindaHomeless Speed — suporte de lentidão; só 1 no campo."""

    nome = "KindaHomeless Speed"
    cost = 75  # v1.2.1: luxo de suporte (era 95); sem buff (papel de suporte)
    damage = 6
    range_px = 160
    fire_rate = 1.8
    slow = True  # ponto forte: aplica lentidão
    asset_name = "speed4"
    description = "Aplica lentidão. Só 1 por vez."
    max_no_campo = 1  # limite de 1 instância (Ancelotti é imune ao slow)


class Speed5(Tower):
    """Speed5 — versátil, com buff ativável (incorpora o antigo Speed6).

    Estado base: sprite `speed5`, stats normais. Ao ativar o buff (clicar na
    torre posicionada), troca para o sprite `speed6` e dobra o dano por 5s; ao
    fim, volta ao sprite base e entra em cooldown de 15s.
    """

    nome = "ShockedSpeed"  # v1.2.1 (era "Speed5")
    cost = 160
    damage = 15      # já com buff v1.2.1 (+5%: 18.9 -> 19)
    range_px = 150
    fire_rate = 1.575  # já com buff v1.2.1 (+5%)
    slow = False
    asset_name = "speed5"
    description = "Versátil. Buff dobra dano por 5s (CD: 15s)."
    cell_radius = 0

    # Duração do buff (segundos).
    BUFF_DURATION: float = 5.0

    def __init__(self, assets, x: float, y: float, cell_x: int, cell_y: int) -> None:
        super().__init__(assets, x, y, cell_x, cell_y)
        self.buff_active: bool = False
        self.buff_timer: float = 0.0
        self.buff_cooldown: float = 15.0
        self.cooldown_timer: float = 0.0
        # Sprites base (speed5) e de buff (speed6). O buff troca self.sprite
        # apenas nas transições, para não conflitar com o swap global do Speed7.
        self._sprite_base: pygame.Surface = self.sprite
        try:
            self._sprite_buff: pygame.Surface = pygame.transform.smoothscale(
                assets.get("speed6"), (SPRITE_SIZE, SPRITE_SIZE)
            )
        except KeyError:
            self._sprite_buff = self._sprite_base  # asset ausente: mantém o base

    def activate_buff(self) -> bool:
        """Ativa o buff se possível (não ativo e fora de cooldown). Retorna sucesso."""
        if not self.buff_active and self.cooldown_timer <= 0.0:
            self.buff_active = True
            self.buff_timer = self.BUFF_DURATION
            self.sprite = self._sprite_buff  # transição: vira modo buff (speed6)
            return True
        return False

    def refresh_sprite(self) -> None:
        """Restaura o sprite correto conforme o estado do buff.

        Usado após o efeito do Speed7 (que troca o sprite de todas as torres por
        speed8 e depois reverte): se o buff ainda está ativo, o sprite deve
        voltar para speed6, não para o base.
        """
        self.sprite = self._sprite_buff if self.buff_active else self._sprite_base

    def update(self, dt: float, enemies: list[Enemy]) -> Projectile | None:
        """Avança os timers do buff; o dano dobrado é aplicado em effective_damage."""
        if self.buff_active:
            self.buff_timer -= dt
            if self.buff_timer <= 0.0:
                self.buff_active = False
                self.cooldown_timer = self.buff_cooldown
                self.sprite = self._sprite_base  # transição: volta ao base (speed5)
        elif self.cooldown_timer > 0.0:
            self.cooldown_timer -= dt
        return super().update(dt, enemies)

    def effective_damage(self) -> int:
        """Dano (já com upgrade) dobrado enquanto o buff está ativo."""
        return self.damage * 2 if self.buff_active else self.damage


class Speed7(Tower):
    """KillThatBoy — habilidade global: não atira; ao ser usada, hitkill geral."""

    nome = "KillThatBoy"
    cost = 1000
    damage = 0
    range_px = 9999
    fire_rate = 0.0
    slow = False
    asset_name = "speed7"
    description = "Hitkill global. Uso único. Não vendável."
    cell_radius = 1
    max_no_campo = 1  # uso único por partida; só 1 no campo

    def __init__(self, assets, x: float, y: float, cell_x: int, cell_y: int) -> None:
        super().__init__(assets, x, y, cell_x, cell_y)
        self.ability_used: bool = False

    def update(self, dt, enemies):
        # Não atira: sem detecção, sem loop, sem _find_target. range_px alto é
        # apenas simbólico (tooltip) e nunca entra em cálculo de alcance.
        return None

    def draw_range(self, surface: pygame.Surface) -> None:
        """Sem círculo de alcance: range_px é simbólico (evita Surface gigante)."""
        return

    def use_ability(self) -> bool:
        """Marca a habilidade como usada. Retorna True só na primeira chamada."""
        if self.ability_used:
            return False
        self.ability_used = True
        return True


# Fonte única das torres jogáveis — usada pela mão de cartas e pelo posicionamento.
# Speed6 foi unificado ao Speed5 (modo buff), então não é mais uma carta separada.
TOWER_TYPES: list[type[Tower]] = [
    Speed1, Speed2, Speed3, Speed4, Speed5, Speed7
]
