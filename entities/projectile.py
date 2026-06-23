"""Projéteis disparados pelas torres.

Um projétil persegue um inimigo-alvo e, ao colidir, causa dano (resolvido no
game loop). Movimento baseado em delta-time. Render simples: um círculo
colorido (amarelo, ou azul-claro se aplica slow).
"""

import pygame

from entities.enemy import Enemy

# Distância (px) para considerar que o projétil acertou o alvo.
HIT_DISTANCE: float = 8.0
# Raio do círculo desenhado.
RAIO: int = 6


class Projectile:
    """Projétil teleguiado em direção a um inimigo."""

    def __init__(
        self,
        x: float,
        y: float,
        target: Enemy,
        damage: int,
        apply_slow: bool,
        speed: float = 300.0,
    ) -> None:
        self.x: float = float(x)
        self.y: float = float(y)
        self.target: Enemy = target
        self.damage: int = damage
        self.apply_slow: bool = apply_slow
        self.speed: float = speed

    def update(self, dt: float) -> bool:
        """Move em direção ao alvo.

        Retorna True se colidiu (dist <= HIT_DISTANCE) ou o alvo já morreu —
        em ambos os casos o projétil deve ser removido pelo game loop.
        """
        if self.target.is_dead():
            return True

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = (dx * dx + dy * dy) ** 0.5

        if dist <= HIT_DISTANCE:
            return True

        # Avança no máximo `dist` para não ultrapassar o alvo.
        passo = min(self.speed * dt, dist)
        self.x += dx / dist * passo
        self.y += dy / dist * passo
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Círculo amarelo (ou azul-claro se aplica slow)."""
        cor = (120, 180, 255) if self.apply_slow else (255, 210, 40)
        pygame.draw.circle(surface, cor, (int(self.x), int(self.y)), RAIO)
