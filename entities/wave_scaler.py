"""Fórmulas de scaling para o Modo Infinito.

Funções puras — sem estado, sem dependências de pygame.
Todos os parâmetros de balanceamento vêm de config/settings.py.
"""

from config.settings import (
    INF_BOSS_HP_FATOR,
    INF_BOSS_WAVE_INTERVAL,
    INF_QTD_CAP,
    INF_REWARD_CAP_WAVE,
    INF_TC_WAVE_ESCALA,
    INF_TC_WAVE_FAIXA1,
    INF_TC_WAVE_FAIXA2,
    INF_TC_WAVE_FAIXA3,
    INF_VEL_BUFF_WAVE50,
    INF_VEL_CAP_MULT,
    INF_VEL_FATOR,
)


def calcular_hp_inimigo(hp_base: float, wave: int) -> float:
    """Scaling linear por faixas de wave (piecewise, sem explosão exponencial).

    Wave 1-10:  +12%/wave     (ex: labubu1 wave10 = 2.2× base)
    Wave 11-30: +18% adicional por wave a partir do patamar da wave 10
    Wave 31-50: +30% adicional por wave a partir da wave 30
    Wave 51+:   +50% adicional por wave a partir da wave 50
    """
    if wave <= 10:
        mult = 1.0 + wave * 0.12
    elif wave <= 30:
        mult = 2.2 + (wave - 10) * 0.18
    elif wave <= 50:
        mult = 5.8 + (wave - 30) * 0.30
    else:
        mult = 11.8 + (wave - 50) * 0.50
    return hp_base * mult


def calcular_velocidade_inimigo(vel_base: float, wave: int) -> float:
    """Velocidade escala 1.5%/wave, cap em INF_VEL_CAP_MULT× da base.

    A partir da wave 50, aplica multiplicador extra INF_VEL_BUFF_WAVE50.
    """
    fator = min(1.0 + wave * INF_VEL_FATOR, INF_VEL_CAP_MULT)
    if wave >= 50:
        fator *= INF_VEL_BUFF_WAVE50
    return vel_base * fator


def calcular_quantidade_inimigos(wave: int) -> int:
    """Quantidade de inimigos por wave, com cap em INF_QTD_CAP.

    A partir da wave 51, dobra em relação à wave anterior (exponencial),
    até atingir INF_QTD_CAP.
    """
    if wave <= 5:
        qtd = 3 + wave           # 4, 5, 6, 7, 8
    elif wave <= 15:
        qtd = 8 + (wave - 5)    # 9 … 18
    elif wave <= 30:
        qtd = 18 + (wave - 15)  # 19 … 33
    elif wave <= 50:
        qtd = 33 + (wave - 30) // 5  # cresce devagar até 37
    else:
        _base_50 = 33 + (50 - 30) // 5  # 37
        qtd = _base_50 * (2 ** (wave - 50))
    return min(qtd, INF_QTD_CAP)


def e_boss_wave(wave: int) -> bool:
    """True se a wave é múltipla de INF_BOSS_WAVE_INTERVAL."""
    return wave > 0 and wave % INF_BOSS_WAVE_INTERVAL == 0


def calcular_hp_boss(hp_base_boss: float, wave: int) -> float:
    """HP do boss: cresce 40% a cada boss wave.

    Boss da wave 10: hp_base × 1.4^1
    Boss da wave 20: hp_base × 1.4^2
    Boss da wave 30: hp_base × 1.4^3 ...
    """
    n_boss = max(1, wave // INF_BOSS_WAVE_INTERVAL)
    return hp_base_boss * (INF_BOSS_HP_FATOR ** n_boss)


def calcular_recompensa_kill(recompensa_base: float, wave: int) -> int:
    """Recompensa por kill escala com a wave; cap na wave INF_REWARD_CAP_WAVE."""
    w = min(wave, INF_REWARD_CAP_WAVE)
    if w <= 10:
        mult = 1.0
    elif w <= 30:
        mult = 1.5
    elif w <= 50:
        mult = 2.2
    else:
        mult = 2.2 + (w - 50) * 0.05
    return max(1, round(recompensa_base * mult))


def calcular_bonus_wave(wave: int) -> int:
    """Bônus em TexasCoins ao completar a wave (todos os inimigos eliminados).

    Boss waves (múltiplo de INF_BOSS_WAVE_INTERVAL) dão 3× o bônus da faixa.
    """
    if wave <= 10:
        base = 50
    elif wave <= 30:
        base = 100
    elif wave <= 50:
        base = 200
    else:
        base = 300 + wave * 5
    return base * 3 if e_boss_wave(wave) else base


def calcular_tc_por_kill(wave: int) -> int:
    """TexasCoins concedidos por kill no Modo Infinito.

    Faixas: wave 1-10 → 25 TC/kill, 11-20 → 50 TC/kill, 21-30 → 75 TC/kill.
    Acima de 30 escala +25 TC a cada 10 waves extras.
    """
    if wave <= 10:
        return INF_TC_WAVE_FAIXA1
    if wave <= 20:
        return INF_TC_WAVE_FAIXA2
    if wave <= 30:
        return INF_TC_WAVE_FAIXA3
    extras = (wave - 31) // 10 + 1
    return INF_TC_WAVE_FAIXA3 + extras * INF_TC_WAVE_ESCALA


def escolher_tipos_wave(wave: int) -> list[str]:
    """Tipos de inimigos comuns a spawnar nesta wave (não incluem o boss).

    Progressão: mais fracos no início, mais tanques depois.
    """
    if wave <= 5:
        return ["labubu1", "labubu2"]
    elif wave <= 15:
        return ["labubu2", "labubu3"]
    elif wave <= 30:
        return ["labubu3", "labubu4"]
    else:
        return ["labubu4", "labubu3"]


def intervalo_spawn(wave: int) -> float:
    """Intervalo entre spawns individuais (decresce com a wave, mínimo 0.4s)."""
    return max(0.4, 1.5 - wave * 0.02)
