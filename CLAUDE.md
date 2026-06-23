# Speed Vs Labubu — CLAUDE.md

## Visão Geral
Tower defense 2D em Python/Pygame. O jogador posiciona cartas "Speed" no campo para defender contra ondas de Labubus. O boss final é Ancelotti.

## Stack
- **Python 3.11+**
- **Pygame 2.x** — renderização, input, game loop
- **pygame-gui** — UI de menus, HUD, botões (simples e bem documentado)
- **Pillow** — pré-processamento de assets se necessário

## Regras de Arquitetura
1. Nunca misturar lógica de jogo com renderização — separar em camadas distintas
2. Nunca usar caminhos absolutos — sempre `pathlib.Path` relativo à raiz do projeto
3. Nunca bloquear o game loop principal — sem `time.sleep()` fora do loop de eventos
4. Todo asset carregado uma única vez no boot via `AssetManager`, nunca em runtime
5. Estados do jogo gerenciados por `GameStateManager` (menu, jogo, pausa, game over)
6. Path dos inimigos definido como lista de coordenadas em `config/path.json` — nunca hardcoded
7. Comentários e mensagens de erro em PT-BR
8. Cada classe em seu próprio arquivo dentro do módulo correto

## Estrutura de Pastas
```
Speed Vs Labubu Remake/
├── CLAUDE.md
├── ARCHITECTURE.md
├── PLAN.md
├── main.py                  # Entrypoint
├── config/
│   ├── settings.py          # Constantes globais (resolução, FPS, cores)
│   └── path.json            # Coordenadas do path dos inimigos no mapa
├── core/
│   ├── game.py              # Game loop principal
│   ├── state_manager.py     # Máquina de estados
│   └── asset_manager.py     # Carregamento e cache de assets
├── entities/
│   ├── tower.py             # Classe base Torre (Speed)
│   ├── enemy.py             # Classe base Inimigo (Labubu)
│   ├── boss.py              # Ancelotti (herda de Enemy)
│   ├── projectile.py        # Projéteis das torres
│   └── wave_manager.py      # Controle de ondas
├── map/
│   ├── game_map.py          # Renderização do mapa + grid
│   └── placement_grid.py    # Lógica de células livres/bloqueadas
├── ui/
│   ├── hud.py               # Vida, moedas, onda atual
│   ├── card_hand.py         # Mão de cartas do jogador (bottom bar)
│   └── menus.py             # Menu principal, pause, game over
├── assets/
│   ├── mapa/
│   │   └── mapa.png
│   ├── speeds/
│   │   ├── speed1.png
│   │   ├── speed2.png
│   │   ├── speed3.png
│   │   └── speed4.png
│   └── labubus/
│       ├── labubu1.png
│       ├── labubu2.png
│       ├── labubu3.png
│       ├── labubu4.png
│       └── ancelotti.png
└── requirements.txt
```

## Convenções de Código
- snake_case para variáveis e funções
- PascalCase para classes
- Constantes em UPPER_CASE em `config/settings.py`
- Type hints em todas as funções públicas
- Nenhum `print()` em produção — usar `logging`

## Comandos Úteis
```bash
# Instalar dependências
pip install pygame pygame-gui Pillow

# Rodar o jogo
python main.py

# Rodar uma etapa específica de desenvolvimento
python main.py --dev  # modo dev com grid visível e FPS counter
```
