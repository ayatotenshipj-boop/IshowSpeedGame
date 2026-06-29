"""DrivingCar Speed — torre buffer de aceleração de ataque global.

Tipo: Buffer (não causa dano, não atira).
Skill ativável: ao clicar na torre posicionada, acelera fire_rate de todas as
torres ativas em campo (+80% no nível 1, +120% no nível máximo) por 40s.
Cooldown: 15s após o término do buff. Stacking desativado: ativar enquanto
buff já estiver ativo não tem efeito.
Alcance: 85 base (apenas para exibição — sem detecção de alvo).
Raridade: Limitado (obtida via gacha com pity em 120 pulls).
"""

import logging

from entities.tower import Tower

logger = logging.getLogger(__name__)

# Multiplicadores de fire_rate: nível 1 → +80%, nível máximo → +120%.
BUFF_MULT_BASE: float = 1.80   # +80% = fator 1.8× (nível 1)
BUFF_MULT_MAX: float  = 2.20   # +120% = fator 2.2× (nível máximo)
BUFF_DURATION: float  = 40.0   # segundos de duração do buff
BUFF_COOLDOWN: float  = 15.0   # segundos de cooldown após o buff
RANGE_BASE: int = 85


class DrivingCarSpeed(Tower):
    """Torre buffer: skill ativável que acelera fire_rate global. Não atira."""

    nome = "DrivingCar Speed"
    cost = 300
    damage = 0
    range_px = RANGE_BASE
    fire_rate = 0.0
    slow = False
    asset_name = "speed9"
    description = "Skill ativavel: +80% SPA global (120% max). Nao acumula."
    max_no_campo = 1

    def __init__(self, assets, x: float, y: float, cell_x: int, cell_y: int) -> None:
        super().__init__(assets, x, y, cell_x, cell_y)
        self.skill_ativa: bool = False
        self.skill_timer: float = 0.0
        self.cooldown_timer: float = 0.0
        self._towers_buffadas: list = []  # referências das torres que receberam o buff

    def _buff_mult(self) -> float:
        """Multiplicador conforme nível: 1.8× (nível 1), 2.0× (nível 2), 2.2× (nível 3)."""
        return 1.60 + 0.20 * self.level

    def activate_skill(self, towers: list) -> bool:
        """Ativa o buff em todas as torres no campo. Retorna True se ativou.

        Não faz nada se o buff já estiver ativo (anti-stack).
        """
        if self.skill_ativa:
            logger.warning("DrivingCarSpeed: buff já ativo — ativação ignorada.")
            return False
        if self.cooldown_timer > 0.0:
            logger.warning(
                "DrivingCarSpeed: em cooldown (%.0fs restantes) — ativação ignorada.",
                self.cooldown_timer,
            )
            return False

        mult = self._buff_mult()
        self._towers_buffadas = [t for t in towers if t is not self and t.fire_rate > 0]
        for t in self._towers_buffadas:
            t.fire_rate *= mult

        self.skill_ativa = True
        self.skill_timer = BUFF_DURATION
        pct = round((mult - 1) * 100)
        logger.info(
            "DrivingCarSpeed: buff +%d%% SPA aplicado a %d torres.",
            pct, len(self._towers_buffadas),
        )
        return True

    def _desativar_skill(self) -> None:
        """Reverte o buff de fire_rate usando divisão (evita acúmulo de erro)."""
        mult = self._buff_mult()
        for t in self._towers_buffadas:
            if t.fire_rate > 0:
                t.fire_rate /= mult
        self._towers_buffadas = []
        self.skill_ativa = False
        self.cooldown_timer = BUFF_COOLDOWN
        logger.info("DrivingCarSpeed: buff expirado — fire_rate revertido.")

    def update(self, dt: float, enemies: list) -> None:
        """Gerencia timers do buff e cooldown. Não atira."""
        if self.skill_ativa:
            self.skill_timer -= dt
            if self.skill_timer <= 0.0:
                self._desativar_skill()
        elif self.cooldown_timer > 0.0:
            self.cooldown_timer -= dt
        return None

    def draw_range(self, surface) -> None:
        """Sem círculo de alcance em combate — range é só para exibição."""
        return
