# FIXES_AND_IMPROVEMENTS.md
# Speed Vs Labubu Remake — Correções e Melhorias Pendentes

Gerado após revisão pós-Etapa 8 + análise de gameplay.
Implementar na ordem listada. Não pular itens.

---

## BLOCO 1 — BUGS CRÍTICOS (implementar primeiro)

### 1.1 Tela cheia e dimensionamento adaptativo
**Problema:** jogo tem resolução fixa 1280×720, quebra em telas diferentes e fullscreen.
**Solução:**
- Detectar resolução do monitor com `pygame.display.get_desktop_sizes()[0]`
- Calcular fator de escala: `scale = min(screen_w / 1280, screen_h / 720)`
- Renderizar tudo em Surface interna 1280×720, depois escalar para a resolução real com `pygame.transform.scale`
- Adicionar em `config/settings.py`: `RENDER_WIDTH=1280`, `RENDER_HEIGHT=720`
- `main.py`: criar `render_surface = pygame.Surface((1280, 720))`, desenhar tudo nela, depois `screen.blit(pygame.transform.scale(render_surface, screen_size), (0,0))`
- Suporte a fullscreen via tecla F11: toggle entre windowed e fullscreen
- Ajustar todos os eventos de mouse para converter coordenadas reais → coordenadas da render_surface: `mouse_x = event.pos[0] / scale_x`

### 1.2 Vitória após Wave 15 não exibe tela
**Problema:** jogo não encerra com tela de vitória após boss morrer na onda 15.
**Solução:**
- Verificar condição: `wave_manager.is_finished() and not game_state.enemies and game_state.boss_defeated`
- Tela de vitória deve exibir:
  - Imagem placeholder `assets/dialogs/victory_image.png` centralizada (se não existir, retângulo dourado com texto "[ IMAGEM DE VITÓRIA ]")
  - Mensagem: "Parabéns! Você derrotou Ancelotti!"
  - Submensagem: "Você recebe: [ RECOMPENSA ]" (placeholder, usuário preencherá depois)
  - Kills totais e moedas restantes
  - Botões: "Jogar Novamente" e "Menu Principal"
- Atualizar `VictoryScreen` em `ui/menus.py` para aceitar `victory_image_path` opcional

### 1.3 Path dos inimigos invisível por padrão
**Problema:** trilha vermelha do caminho aparece sempre, deveria ser invisível até jogador selecionar uma carta.
**Solução:**
- Em `main.py`, `draw_path()` só é chamado quando `game_state.selected_card is not None`
- Quando nenhuma carta selecionada: path completamente invisível
- Quando carta selecionada: overlay verde em área livre + trilha vermelha no path (comportamento atual)
- Remover qualquer chamada a `draw_path()` fora do bloco `if selected_card is not None`

### 1.4 Posicionamento livre com hitbox reduzida
**Problema:** torres travadas em grid de 64×64, hitbox muito grande.
**Solução:**
- Torres posicionam no pixel exato do clique (sem snap para célula)
- Hitbox de colisão de cada Speed reduzida para 50% do CELL_SIZE: `HIT_RADIUS = CELL_SIZE * 0.25` (raio, não diâmetro)
- Verificação de sobreposição entre torres: distância entre centros > `HIT_RADIUS * 2`
- Verificação com path: checar se o centro da torre cai em célula PATH no grid
- `set_occupied()` marca apenas a célula central onde a torre foi colocada
- Speed3 e Speed7 com `cell_radius=1` continuam bloqueando área maior

---

## BLOCO 2 — INTRO E MENU PRINCIPAL

### 2.1 Menu principal refeito — visual adequado
**Problema:** tela de menu feia e sem relação com a intro/história do jogo.
**Solução:**
- Menu principal usa `assets/mapa/mapa.png` como fundo (ou versão escurecida)
- Título "SPEED VS LABUBU" em fonte grande, estilo impactante, com sombra
- Sprite do Speed e do Ancelotti nos cantos opostos da tela de menu
- Botões centralizados com estilo consistente com o restante do jogo:
  - **JOGAR**
  - **CONQUISTAS** → abre painel com texto "Em breve..." e botão Fechar
  - **MULTIJOGADOR** → abre painel com texto "Em breve..." e botão Fechar  
  - **SAIR**
- Música `sound.mp3` já tocando suavemente no menu (fade-in após intro)

### 2.2 Cena de intro — fundo dinâmico, não preto
**Problema:** intro tem fundo preto simples, parece desconectada do jogo.
**Solução:**
- Fundo da intro: `assets/mapa/mapa.png` escurecido com overlay `(0,0,0,160)` — sensação de "partida prestes a começar"
- Sprites dos personagens maiores e melhor posicionados
- Manter toda a lógica de typewriter, destaque/escurecimento e sequência de 12 falas
- Transição suave (fade) entre intro e menu principal
- A intro é a "abertura do jogo" — deve parecer cinematográfica

### 2.3 Botões de Conquistas e Multijogador no menu
**Solução:**
- `ConquistasScreen` em `ui/menus.py`: painel centralizado 600×400px, texto "🏆 Conquistas — Em breve...", botão Fechar
- `MultijogorScreen` em `ui/menus.py`: painel centralizado 600×400px, texto "🌐 Multijogador Online — Em breve...", botão Fechar
- Ambos acessíveis pelo menu principal sem sair para outro estado de jogo

---

## BLOCO 3 — FUNCIONALIDADES DE GAMEPLAY

### 3.1 Botão 2× Speed (velocidade do jogo)
**Solução:**
- Adicionar `game_state.speed_multiplier: float = 1.0`
- Botão `[2×]` no HUD durante PLAYING — toggle entre 1.0 e 2.0
- Quando ativo: `dt_efetivo = dt * game_state.speed_multiplier`
- Usar `dt_efetivo` em todos os updates: inimigos, torres, projéteis, wave_manager, timers de áudio
- Indicador visual no botão: `[1×]` cinza / `[2×]` dourado piscante
- Incluir no `reset_game()`: `speed_multiplier = 1.0`

### 3.2 Auto-Skip entre ondas
**Solução:**
- Durante intervalo entre ondas (quando `next_wave_in > 0`), exibir botão `[⏩ SKIP +$bonus]` no HUD
- Bônus de moedas ao skipar: `bonus = int(next_wave_in * 3)` (3 moedas por segundo restante)
- Ao clicar: zerar `wave_timer` no `WaveManager`, adicionar bônus às moedas
- Botão desaparece quando onda começa

---

## BLOCO 4 — SISTEMA DE UPDATE AUTOMÁTICO (documentação de intenção)

**Nota:** funcionalidade ideada durante sessão, não implementada ainda. Documentar para referência futura.

### Conceito
- Arquivo `version.json` no repositório GitHub com versão atual e lista de arquivos atualizáveis
- Ao iniciar o jogo (compilado com PyInstaller), verificar versão remota via `urllib.request`
- Se versão remota > local: exibir tela de update, baixar apenas arquivos alterados, reiniciar
- Pasta gravável para updates: `os.path.dirname(sys.executable)` (não `_MEIPASS`)
- `AssetManager._resolve_path()` checa pasta do `.exe` antes de `_MEIPASS`

### O que falta implementar
- `core/updater.py` com `Updater.check_update()`, `download_files()`, `restart_game()`
- `ui/update_screen.py` com barra de progresso
- `version.json` na raiz do projeto
- Integração no início do `main.py` antes do `pygame.init()`

---

## BLOCO 5 — MODO ONLINE 2 PLAYERS (documentação de intenção)

**Nota:** funcionalidade ideada, não implementada. Alta complexidade — documentar para referência futura.

### Conceito
- Dois jogadores no mesmo mapa, cada um com metade do campo para posicionar torres
- Campo dividido verticalmente: jogador 1 lado esquerdo, jogador 2 lado direito
- Vida compartilhada — inimigos que passam afetam ambos
- Comunicação via sockets (biblioteca `socket` stdlib ou `websockets`)
- Arquitetura: host/client simples, host roda a lógica do jogo e envia estado, client envia inputs

### Estimativa de esforço
- Alta complexidade — exigiria refatorar `GameState` para ser serializável (JSON/pickle)
- `main.py` teria que separar loop de lógica do loop de render
- Mínimo estimado: 2–3 semanas de desenvolvimento

---

## ORDEM DE IMPLEMENTAÇÃO RECOMENDADA

```
1.3 (path invisível)     — 1 arquivo, baixo risco
1.4 (posicionamento livre) — main.py + placement_grid.py
1.1 (dimensionamento)    — main.py, impacta tudo, fazer por último no bloco 1
1.2 (tela de vitória)    — ui/menus.py
2.2 (intro com fundo)    — ui/intro_scene.py
2.1 (menu refeito)       — ui/menus.py
2.3 (conquistas/multi)   — ui/menus.py
3.2 (auto-skip)          — wave_manager.py + main.py + hud.py
3.1 (2× speed)           — game_state.py + main.py + hud.py
```

---

## ASSETS PENDENTES (usuário deve adicionar manualmente)

- `assets/dialogs/victory_image.png` — imagem de vitória (placeholder aceito)
- `assets/sounds/sound.mp3` — música de fundo
- `assets/audio/killthatboy.mp3`
- `assets/audio/suspensemusic.mp3`
- `assets/speeds/speed5.png` até `speed8.png`
