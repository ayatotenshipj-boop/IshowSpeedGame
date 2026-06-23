# Speed Vs Labubu — PLAN.md

## Metodologia
Cada etapa é independente e testável. Não avançar para a próxima sem a atual funcionando.
Rodar `python main.py` ao fim de cada etapa para validar.

---

## Etapa 1 — Setup e Esqueleto do Projeto
**Objetivo:** Janela abrindo, assets carregando, estrutura de pastas criada.

- [ ] Criar `requirements.txt` com `pygame`, `pygame-gui`, `Pillow`
- [ ] Criar `config/settings.py` com `WINDOW_WIDTH=1280`, `WINDOW_HEIGHT=720`, `FPS=60`, `CELL_SIZE=64`, cores base
- [ ] Criar `core/asset_manager.py` — carrega e cacheia todas as imagens de `assets/`
- [ ] Criar `main.py` — inicializa pygame, abre janela 1280x720, roda loop vazio
- [ ] Validar: janela abre sem erros, título "Speed Vs Labubu"

---

## Etapa 2 — Mapa e Grid
**Objetivo:** Mapa renderizado com grid de células visível.

- [ ] Criar `map/game_map.py` — carrega e renderiza `assets/mapa/mapa.png` escalado para `MAP_RECT`
- [ ] Criar `config/path.json` — definir waypoints do path manualmente baseado na imagem do mapa
- [ ] Criar `map/placement_grid.py` — converte waypoints em células `PATH`, resto como `FREE`
- [ ] Renderizar grid em modo dev (linhas cinzas, células PATH em vermelho semi-transparente)
- [ ] Validar: mapa aparece com grid sobreposto, path vermelho visível

---

## Etapa 3 — Sistema de Cartas e Posicionamento
**Objetivo:** Jogador consegue selecionar e posicionar torres.

- [ ] Criar `ui/card_hand.py` — renderiza 4 cartas de Speed na barra inferior com custo em moedas
- [ ] Implementar clique em carta → estado "selecionada" (highlight)
- [ ] Implementar clique em célula FREE → posiciona torre, desconta moedas, célula vira `OCCUPIED`
- [ ] Criar `entities/tower.py` — classe base com `sprite`, `cost`, `damage`, `range`, `fire_rate`
- [ ] Criar Speed1, Speed2, Speed3, Speed4 como subclasses simples
- [ ] Validar: posicionar torre no mapa, não conseguir posicionar no path

---

## Etapa 4 — Inimigos e Movimento
**Objetivo:** Labubus caminhando pelo path.

- [ ] Criar `entities/enemy.py` — classe base com `hp`, `speed`, `reward`, `sprite`
- [ ] Implementar movimento por waypoints: inimigo anda de waypoint em waypoint suavemente
- [ ] Criar Labubu1, Labubu2, Labubu3, Labubu4 como subclasses
- [ ] Criar `entities/wave_manager.py` — spawna inimigos em intervalos definidos
- [ ] Validar: Labubus aparecem e andam pelo path até o fim

---

## Etapa 5 — Combate
**Objetivo:** Torres atacam inimigos, inimigos morrem.

- [ ] Criar `entities/projectile.py` — projétil com velocidade, dano, target
- [ ] Torres detectam inimigos no raio de alcance e disparam projéteis
- [ ] Projétil colide com inimigo → subtrai HP
- [ ] Inimigo com HP ≤ 0 → remove da lista, adiciona moedas ao jogador
- [ ] Inimigo que chega ao fim do path → subtrai vida do jogador
- [ ] Validar: torres atiram, inimigos morrem, vida cai ao chegar no fim

---

## Etapa 6 — HUD e Estados
**Objetivo:** HUD funcional, estados de jogo completos.

- [ ] Criar `ui/hud.py` — renderiza vida, moedas, número da onda atual
- [ ] Criar `core/state_manager.py` — máquina de estados MENU/PLAYING/PAUSED/GAME_OVER/VICTORY
- [ ] Criar `ui/menus.py` com pygame-gui — tela de Menu principal (Jogar / Sair)
- [ ] Tela de Pause (ESC) com pygame-gui — Continuar / Menu Principal
- [ ] Tela de Game Over e Victory
- [ ] Validar: fluxo completo de estados funciona

---

## Etapa 7 — Boss Ancelotti
**Objetivo:** Boss implementado com comportamento especial.

- [ ] Criar `entities/boss.py` — herda de Enemy, HP muito alto
- [ ] Comportamento: ao receber dano, chance de spawnar Labubu1 próximo
- [ ] Imune ao efeito de slow do Speed4
- [ ] Sprite maior (128x128 ou 256x256) escalado no mapa
- [ ] WaveManager spawna Ancelotti na última onda
- [ ] Validar: boss aparece, spawna inimigos, morre corretamente

---

## Etapa 8 — Polimento
**Objetivo:** Jogo jogável e agradável.

- [ ] Animações simples de sprite (se assets tiverem frames)
- [ ] Efeito visual ao posicionar torre (flash verde)
- [ ] Efeito visual ao inimigo morrer (flash vermelho ou partícula simples)
- [ ] Som básico (opcional — pygame.mixer)
- [ ] Balancear custo das torres e HP dos inimigos
- [ ] Modo dev com `--dev` flag: grid visível, HP bars, FPS counter
- [ ] Validar: partida completa do menu ao game over/victory

---

## Dependências entre Etapas
```
1 → 2 → 3
        └→ 4 → 5 → 6 → 7 → 8
```

## Notas para o Claude Code
- Sempre checar `CLAUDE.md` antes de criar qualquer arquivo
- Nunca usar `os.path` — sempre `pathlib.Path`
- Nunca carregar asset fora do `AssetManager`
- O path.json deve ser ajustado visualmente testando no modo dev da Etapa 2
- pygame-gui só é usado para menus — HUD e cartas são Pygame puro para mais controle visual
