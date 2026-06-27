---
name: pygame-ui-adapter
description: Use este skill quando qualquer tarefa envolver adaptação visual de UI em Pygame. Cobre: refatoramento de superfícies, paletas, fontes, layouts de HUD, cartas, modais e telas de menu — sem quebrar lógica de jogo existente.
---

# Pygame UI Adapter Skill

## Princípio central
Adaptar visualmente sem substituir. Toda modificação deve ser cirúrgica: localizar o trecho exato, entender o contexto, editar apenas o que toca na camada de render. Nunca alterar lógica de update, física de inimigos, economia ou sistemas de estado.

## Antes de qualquer edição

1. Mapear todos os arquivos que contêm chamadas de render:
   - `ui/card_hand.py` — cartas e tooltip
   - `ui/hud.py` — stats, cronômetro, boss alerta
   - `ui/menus.py` — menu, pause, gameover, victory, conquistas, changelog, update
   - `ui/intro_scene.py` — cena de diálogo
   - `ui/leaderboard_screen.py` — tabela online
   - `ui/nome_vitoria_screen.py` — input de nome
   - `ui/update_screen.py` — progresso de download
   - `ui/conquistas_screen.py` — conquistas
   - `ui/modo_screen.py` — seleção de dificuldade
   - `map/game_map.py` — render do mapa
   - `map/placement_grid.py` — path e overlay de posicionamento
   - `main.py` — composição final de camadas

2. Para cada arquivo, listar:
   - Quais `pygame.Surface`, `pygame.Rect` e `pygame.font` são criados
   - Quais cores são usadas como literais (ex: `(30, 30, 46)`) versus constantes de `settings.py`
   - Quais chamadas de `draw` dependem de posição calculada em runtime vs fixas

3. Nunca editar sem ter lido o arquivo completo nessa sessão.

## Regras de edição

- **Cores**: centralizar em `config/settings.py`. Nunca usar tupla literal de cor fora de `settings.py` exceto em código de transição temporária.
- **Fontes**: instanciar no `__init__` da classe, nunca dentro de `draw()` ou `update()`.
- **Surfaces de overlay**: cachear como atributo de instância, nunca criar dentro do loop de render.
- **Posições**: calcular relativas a `MAP_RECT`, `HUD_RECT` ou `WINDOW_WIDTH/HEIGHT` de `settings.py`. Nunca hardcodar pixels absolutos sem referência a uma constante.
- **`pygame_gui`**: usar apenas em `ui/menus.py` e inicialização em `main.py`. HUD e cartas em Pygame puro.
- **Ordem de camadas**: respeitar sempre: `game_map` → torres → projéteis → inimigos → overlays → HUD → modais. Nunca inverter.

## Paleta do projeto (fonte de verdade)

Definida em `config/settings.py`. Qualquer cor nova deve ser adicionada lá com nome semântico antes de ser usada. Nomes convencionados:

```python
# Campo
COR_CAMPO_BASE       = (30, 64, 16)
COR_CAMPO_LINHA      = (255, 255, 255, 18)   # alpha para SRCALPHA

# UI base
COR_FUNDO_HUD        = (8, 8, 6)
COR_FUNDO_CARTA      = (15, 15, 6)
COR_BORDA_CARTA      = (42, 42, 16)
COR_BORDA_ATIVA      = (255, 208, 64)
COR_BORDA_SUTIL      = (37, 34, 0)

# Texto
COR_TEXTO_PRIMARIO   = (240, 240, 232)
COR_TEXTO_SECUNDARIO = (100, 100, 64)
COR_TEXTO_DESATIVO   = (50, 50, 32)

# Acento
COR_DOURADO          = (255, 208, 64)
COR_DOURADO_ESCURO   = (184, 120, 0)
COR_VERDE_NEON       = (127, 255, 58)
COR_CIANO            = (0, 255, 204)
COR_VERMELHO         = (212, 43, 30)
COR_LARANJA          = (255, 140, 0)
COR_ROXO             = (192, 80, 255)
COR_AZUL             = (74, 176, 255)
```

## Fontes disponíveis

```python
# Em __init__ de cada classe UI:
self.fonte_titulo    = pygame.font.SysFont("Impact", 32)        # títulos de tela
self.fonte_carta     = pygame.font.SysFont("monospace", 11)     # nomes nas cartas
self.fonte_stats     = pygame.font.SysFont("monospace", 10)     # stats e descrição
self.fonte_hud       = pygame.font.SysFont("monospace", 13)     # HUD de jogo
self.fonte_hud_bold  = pygame.font.SysFont("monospace", 14, bold=True)
self.fonte_grande    = pygame.font.SysFont("Impact", 48)        # vitória/game over
```

## Checklist antes de marcar edição como completa

- [ ] `python main.py` abre sem `AttributeError` ou `TypeError` em nenhuma tela
- [ ] `python main.py --dev` abre sem erro
- [ ] Nenhuma `Surface` criada dentro de `draw()` ou `update()`
- [ ] Nenhuma cor literal `(r, g, b)` fora de `settings.py`
- [ ] Nenhuma fonte instanciada fora de `__init__`
- [ ] Ordem de camadas de render preservada em `main.py`
- [ ] Nenhum sistema de lógica (movimento, economia, ondas, leaderboard) alterado
