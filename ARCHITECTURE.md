# Speed Vs Labubu — ARCHITECTURE.md

## Diagrama de Camadas

```
┌─────────────────────────────────────────┐
│                  main.py                │  ← Entrypoint + Game Loop
│    handle_events → update → render      │    (loop real aqui, não em módulo separado)
├─────────────────────────────────────────┤
│  StateManager (core/state_manager.py)   │  ← Máquina de estados de telas (GameScreen)
│  GameState    (core/game_state.py)      │  ← @dataclass: dados mutáveis da partida
├──────────────────┬──────────────────────┤
│   LÓGICA (update)│  RENDER (draw)       │
│                  │                      │
│  WaveManager     │  GameMap             │
│  PlacementGrid   │  HUD                 │
│  Tower           │  CardHand            │
│  Enemy / Boss    │  Menus               │
│  Projectile      │                      │
├──────────────────┴──────────────────────┤
│  AssetManager (core/asset_manager.py)   │  ← Cache de imagens (PNG)
│  AudioManager (core/audio.py)           │  ← Música e efeitos sonoros
├─────────────────────────────────────────┤
│         config/settings.py              │  ← Constantes globais
│         config/path.json                │  ← Waypoints do path
└─────────────────────────────────────────┘
```

## Fluxo de Estados

8 telas definidas em `core/state_manager.py` (`GameScreen` enum):

```
[MENU]
  └─ Jogar ──► [SELECAO_MODO]  (escolha de dificuldade)
                 └──────────► [INTRO]  (cena de diálogo/cutscene)
                                └──────► [PLAYING]
                                           ├─ ESC ──► [PAUSED] ──► Continuar ──► [PLAYING]
                                           ├─ Vida = 0 ──► [GAME_OVER]
                                           └─ Todas ondas vencidas ──► [NOME_VITORIA]
                                                                          └──► [VICTORY]
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

6 torres jogáveis em `entities/tower.py` (ver `TOWER_TYPES`):
```
Speed1 — torre básica, barata, ataque rápido e fraco
Speed2 — alcance amplo, cadência lenta (sem AoE)
Speed3 — sniper: dano massivo, alcance curto, cadência lenta
Speed4 — AoE de slow: não causa dano, desacelera todos no range
Speed5 — versátil; buff ativável dobra dano por 40s com AoE a cada 6s (CD: 15s); usa sprite speed6 no buff
Speed7 — hitkill global (uso único por partida): mata todos os inimigos ao ser ativada; custo 1000
```
Obs: speed6.png = sprite do buff do Speed5. speed8.png = sprite visual de todas as torres durante o efeito do Speed7. Não são cartas separadas.

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

## GameState vs. StateManager

Distinção importante entre os dois módulos de estado:

| Módulo | Classe | Papel |
|--------|--------|-------|
| `core/state_manager.py` | `StateManager` + enum `GameScreen` | Qual **tela** está ativa |
| `core/game_state.py` | `@dataclass GameState` | **Dados** da partida em curso (moedas, vidas, torres, inimigos, timers, dificuldade, VFX) |

## UI com pygame-gui

- `pygame_gui.UIManager` inicializado uma vez em `main.py`
- Menus usam `UIButton`, `UILabel`, `UIPanel` do pygame-gui
- HUD desenhado manualmente com Pygame (mais controle visual)
- `CardHand` desenhada manualmente na `HUD_RECT`
