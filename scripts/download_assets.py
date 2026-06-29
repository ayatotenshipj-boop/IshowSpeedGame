"""
Script de download de assets externos (fontes e ícones).
Rodar UMA VEZ antes do primeiro build: python scripts/download_assets.py
Não executar dentro do jogo em runtime.

Fontes: licença OFL — livre para uso comercial.
Ícones game-icons.net: licença CC BY 3.0 — ver CREDITS.md.
"""

from pathlib import Path
import urllib.request
import sys

RAIZ = Path(__file__).resolve().parent.parent
FONTS_DIR = RAIZ / "assets" / "fonts"
ICONS_DIR = RAIZ / "assets" / "icons"
FONTS_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR.mkdir(parents=True, exist_ok=True)

# ─── Fontes (OFL) ────────────────────────────────────────────────────────────
FONTES: dict[str, str] = {
    "BebasNeue.ttf": (
        "https://github.com/dharmatype/Bebas-Neue/raw/master/fonts/"
        "BebasNeue(2018)ByDhamraType/TTF/BebasNeue-Regular.ttf"
    ),
    "Orbitron-Bold.ttf": (
        "https://github.com/googlefonts/orbitron-vf/raw/master/fonts/ttf/Orbitron-Bold.ttf"
    ),
    "Orbitron-Regular.ttf": (
        "https://github.com/googlefonts/orbitron-vf/raw/master/fonts/ttf/Orbitron-Regular.ttf"
    ),
    "PressStart2P-Regular.ttf": (
        "https://github.com/google/fonts/raw/main/ofl/pressstart2p/PressStart2P-Regular.ttf"
    ),
}

# ─── Ícones game-icons.net (CC BY 3.0 — ver CREDITS.md) ─────────────────────
# Padrão de URL: https://game-icons.net/icons/{cor_icone}/{cor_fundo}/1x1/{autor}/{slug}.png
_BASE = "https://game-icons.net/icons/ffffff/transparent/1x1"
_B = _BASE

ICONES: dict[str, str] = {
    # HUD de gameplay
    "icon_coin.png":         f"{_B}/delapouite/coins.png",
    "icon_heart.png":        f"{_B}/sbed/health-normal.png",
    "icon_skull.png":        f"{_B}/lorc/skull-bolt.png",
    "icon_clock.png":        f"{_B}/lorc/hourglass.png",
    "icon_wave.png":         f"{_B}/lorc/wave-crest.png",
    # Tower panel
    "icon_upgrade.png":      f"{_B}/delapouite/upgrade.png",
    "icon_sell.png":         f"{_B}/delapouite/sell-card.png",
    "icon_range.png":        f"{_B}/lorc/archery-target.png",
    "icon_damage.png":       f"{_B}/lorc/crossed-swords.png",
    "icon_speed_icon.png":   f"{_B}/lorc/run.png",
    "icon_skill.png":        f"{_B}/lorc/lightning-helix.png",
    # Store / Rolls
    "icon_pull.png":         f"{_B}/lorc/rolling-bomb.png",
    "icon_pity.png":         f"{_B}/lorc/guarded-tower.png",
    "icon_limited.png":      f"{_B}/delapouite/star-formation.png",
    "icon_lock.png":         f"{_B}/lorc/padlock.png",
    # Leaderboard
    "icon_trophy.png":       f"{_B}/lorc/trophy.png",
    "icon_timer.png":        f"{_B}/lorc/stopwatch.png",
    "icon_infinity.png":     f"{_B}/lorc/ouroboros.png",
    "icon_sword.png":        f"{_B}/lorc/broadsword.png",
    "icon_target.png":       f"{_B}/lorc/target-arrows.png",
    # Modo Infinito HUD
    "icon_boss_alert.png":   f"{_B}/lorc/evil-fork.png",
    "icon_wave_counter.png": f"{_B}/lorc/wave-crest.png",
    # Boss / inimigos
    "icon_boss.png":         f"{_B}/lorc/minions.png",
}


def baixar(url: str, destino: Path) -> None:
    if destino.exists():
        print(f"  [ok] já existe: {destino.name}")
        return
    print(f"  [↓]  baixando: {destino.name}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            destino.write_bytes(r.read())
        print(f"  [✓]  {destino.name} ({destino.stat().st_size} bytes)")
    except Exception as e:
        print(f"  [✗]  ERRO em {destino.name}: {e}", file=sys.stderr)


if __name__ == "__main__":
    print("\n=== Fontes ===")
    for nome, url in FONTES.items():
        baixar(url, FONTS_DIR / nome)

    print("\n=== Ícones ===")
    for nome, url in ICONES.items():
        baixar(url, ICONS_DIR / nome)

    print("\n[assets] download concluído.")
    print(f"  Fontes em: {FONTS_DIR}")
    print(f"  Ícones em: {ICONS_DIR}")
