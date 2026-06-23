# Speed Vs Labubu — ARCHITECTURE.md

## Diagrama de Camadas

```
┌─────────────────────────────────────────┐
│                  main.py                │  ← Entrypoint, inicializa tudo
├─────────────────────────────────────────┤
│            GameStateManager             │  ← Controla qual estado está ativo
│     MENU → PLAYING → PAUSED → GAMEOVER  │
├─────────────────────────────────────────┤
│               Game Loop                 │  ← core/game.py
│    handle_events → update → render      │
├──────────────────┬──────────────────────┤
│   LÓGICA (update)│  RENDER (draw)       │
│                  │                      │
│  WaveManager     │  GameMap             │
│  PlacementGrid   │  HUD                 │
│  Tower           │  CardHand            │
│  Enemy / Boss    │  Menus (pygame-gui)  │
│  Projectile      │                      │
├──────────────────┴──────────────────────┤
│              AssetManager               │  ← Cache único de imagens/sons
├─────────────────────────────────────────┤
│         config/settings.py              │  ← Constantes globais
│         config/path.json                │  ← Waypoints do path
└─────────────────────────────────────────┘
```

## Fluxo de Estados

```
[MENU] 
  └─ Jogar ──► [PLAYING]
                 ├─ ESC ──► [PAUSED] ──► Continuar ──► [PLAYING]
                 ├─ Vida = 0 ──► [GAME_OVER]
                 └─ Todas ondas vencidas ──► [VICTORY]
```

## Sistema de Grid / Placement

O mapa é dividido em células. Cada célula tem um estado:
- `FREE` — jogador pode posicionar torre
- `PATH` — célula do caminho dos inimigos (bloqueada)
- `OCCUPIED` — torre já posicionada

```python
# config/path.json — lista de waypoints em pixels
{
  "waypoints": [
    {"x": 64, "y": 320},
    {"x": 64, "y": 128},
    {"x": 512, "y": 128},
    ...
  ],
  "cell_size": 64
}
```

O `PlacementGrid` converte os waypoints em células bloqueadas automaticamente.

## Sistema de Cartas (Card Hand)

- Jogador começa com N moedas
- Cada Speed tem um custo em moedas
- Ao clicar numa carta, ela fica "selecionada"
- Ao clicar em célula FREE no mapa, a torre é posicionada e o custo é descontado
- Moedas são ganhas ao matar inimigos

## Entities

### Tower (Speed)
```
Speed1 — torre básica, barata, ataque rápido e fraco
Speed2 — área de efeito pequena
Speed3 — projétil lento mas dano alto
Speed4 — torre de suporte, reduz velocidade dos inimigos
```

### Enemy (Labubu)
```
Labubu1 — fraco, rápido
Labubu2 — médio
Labubu3 — lento, resistente
Labubu4 — rápido e resistente
Ancelotti — Boss: muito HP, imune a slow, spawna Labubus ao ser atingido
```

### Wave Manager
- Ondas definidas em lista de dicts: `[{"enemy": "labubu1", "count": 5, "interval": 1.5}, ...]`
- Intervalo entre ondas: 10 segundos
- Boss aparece na última onda

## Resolução e Assets

```python
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 720
CELL_SIZE     = 64       # células do grid
MAP_RECT      = pygame.Rect(0, 0, 1280, 620)   # área do mapa
HUD_RECT      = pygame.Rect(0, 620, 1280, 100) # barra inferior (cartas + stats)
```

Assets carregados via `AssetManager.get(nome)` — nunca `pygame.image.load()` direto no código de entidade.

## UI com pygame-gui

- `pygame_gui.UIManager` inicializado uma vez em `core/game.py`
- Menus usam `UIButton`, `UILabel`, `UIPanel` do pygame-gui
- HUD desenhado manualmente com Pygame (mais controle visual)
- `CardHand` desenhada manualmente na `HUD_RECT`
