# UI_VISUAL_ADAPTATION.md
# Speed Vs Labubu Remake — Adaptação Visual da UI

## Propósito deste documento

Guiar a adaptação visual da UI do Pygame de forma cirúrgica, sem quebrar nenhum sistema existente. Cada seção tem escopo estrito: o que pode ser tocado, o que é proibido, e o critério de validação.

---

## Agentes e Skills obrigatórios

**Antes de qualquer ação:**

1. Acione `architect-reviewer` (Opus) — ler este documento e mapear dependências entre arquivos de UI antes de qualquer edição
2. Acione `code-reviewer` (Opus) — revisar cada arquivo após edição, antes de passar ao próximo
3. Acione `debugger` (Sonnet) — se qualquer `python main.py` falhar durante o processo
4. Skill obrigatória: `pygame-ui-adapter` em `~/.claude/agents/` ou copiar o conteúdo de `skills/pygame-ui-adapter/SKILL.md` para o contexto antes de começar
5. Skills adicionais: `systematic-debugging`, `verification-before-completion`, `full-output-enforcement`, `karpathy-guidelines`

**Não commitar durante o processo.** Commit apenas após aprovação do relatório final.

---

## FASE 0 — Planejamento (obrigatório antes de qualquer edição)

### 0.1 Mapeamento de arquivos

Antes de editar qualquer coisa, rodar:

```bash
grep -rn "pygame.draw\|surface.blit\|font.render\|pygame.Surface\|fill(" ui/ map/game_map.py map/placement_grid.py main.py | grep -v ".pyc" > /tmp/ui_map.txt
cat /tmp/ui_map.txt
```

Reportar: quantas cores literais `(r, g, b)` existem fora de `settings.py`, quantas `pygame.Surface` são criadas fora de `__init__`, quantas fontes são instanciadas dentro de `draw()`.

### 0.2 Inventário de cores atual

```bash
grep -rn "fill(\|draw\." ui/ main.py | grep -oE "\([0-9]+, *[0-9]+, *[0-9]+" | sort | uniq -c | sort -rn
```

Listar as 10 cores mais usadas. Identificar quais já estão em `settings.py` e quais são literais.

### 0.3 Perguntas de preferência visual (PARAR AQUI)

Antes de continuar, perguntar ao usuário:

**Pergunta 1:** A barra de HUD inferior (onde ficam as cartas) deve ter fundo completamente preto `#000` ou manter um tom levemente esverdeado/terroso para remeter ao campo?

**Pergunta 2:** Os títulos das telas de menu/vitória/game over devem usar fonte `Impact` (peso máximo, estilo estádio) ou `Oswald` (mais moderna, como no mockup HTML)?

**Pergunta 3:** O path dos inimigos no campo — quando visível ao selecionar carta — deve ter setas direcionais animadas (pulsação via `sin`) ou ser estático (mais simples, menos distração)?

**Pergunta 4:** O overlay verde sobre a área de posicionamento livre deve ser bem visível `alpha ~80` ou muito sutil `alpha ~30` (quase invisível, só uma leve tintura)?

Aguardar respostas antes de continuar para FASE 1.

---

## FASE 1 — Centralizar paleta em `config/settings.py`

**Escopo:** apenas `config/settings.py`. Nenhum outro arquivo tocado nesta fase.

**Proibido:** alterar qualquer valor que não seja cor (não mexer em CELL_SIZE, FPS, WINDOW_*, INITIAL_COINS, etc.)

### 1.1 Adicionar bloco de cores ao final de `settings.py`

```python
# ═══════════════════════════════════════════
# PALETA VISUAL — Speed Vs Labubu Remake
# Toda cor usada na UI deve vir daqui.
# ═══════════════════════════════════════════

# Campo
COR_CAMPO_BASE        = (30, 64, 16)
COR_CAMPO_LINHA       = (255, 255, 255)    # usar com alpha separado

# Fundo das UIs
COR_FUNDO_TELA        = (8, 8, 6)
COR_FUNDO_HUD         = (8, 8, 6)
COR_FUNDO_CARTA       = (15, 15, 6)
COR_FUNDO_MODAL       = (10, 10, 6)

# Bordas
COR_BORDA_CARTA       = (42, 42, 16)
COR_BORDA_ATIVA       = (255, 208, 64)     # dourado — carta selecionada
COR_BORDA_BUFF        = (255, 140, 0)      # laranja — Speed5 buff ativo
COR_BORDA_SUTIL       = (37, 34, 0)        # quase invisível
COR_BORDA_MODAL       = (37, 40, 0)
COR_BORDA_MODAL_TOPO  = (255, 208, 64)     # 3px dourado no topo dos painéis

# Texto
COR_TEXTO_PRIMARIO    = (240, 240, 232)
COR_TEXTO_SECUNDARIO  = (100, 100, 64)
COR_TEXTO_DESATIVO    = (50, 50, 32)
COR_TEXTO_LABEL       = (68, 68, 48)       # labels de stats

# Acentos
COR_DOURADO           = (255, 208, 64)
COR_DOURADO_ESCURO    = (184, 120, 0)
COR_VERDE_NEON        = (127, 255, 58)
COR_CIANO             = (0, 255, 204)
COR_VERMELHO          = (212, 43, 30)
COR_LARANJA           = (255, 140, 0)
COR_ROXO              = (192, 80, 255)
COR_AZUL              = (74, 176, 255)

# Overlay de posicionamento (valores RGB — aplicar alpha via Surface.set_alpha)
COR_OVERLAY_LIVRE     = (50, 200, 50)      # verde — área livre
COR_OVERLAY_PATH      = (200, 40, 40)      # vermelho — caminho dos inimigos
COR_OVERLAY_INVALIDO  = (220, 50, 50)      # vermelho — hover inválido
COR_OVERLAY_VALIDO    = (50, 220, 80)      # verde — hover válido

# Alphas padrão (int 0-255)
ALPHA_OVERLAY_GLOBAL  = 45    # overlay verde/vermelho sobre o campo inteiro
ALPHA_OVERLAY_HOVER   = 90    # highlight da célula sob o cursor
ALPHA_MODAL_BG        = 200   # fundo escuro sob modais
ALPHA_PATH_VISIVEL    = 160   # path quando carta selecionada
```

### 1.2 Validação da Fase 1

```bash
python3 -c "from config.settings import COR_DOURADO; print('OK:', COR_DOURADO)"
```

Deve imprimir `OK: (255, 208, 64)` sem erro.

---

## FASE 2 — Migrar cores em `ui/hud.py`

**Escopo:** apenas `ui/hud.py`.

**Proibido:** alterar parâmetros dos métodos, lógica de cálculo de posição, lógica de cronômetro ou lógica de barra de vida.

### 2.1 O que mudar

Substituir todas as tuplas de cor literais por constantes de `settings.py`. Exemplos comuns:

```python
# ANTES
surface.fill((15, 15, 30))
font.render("Onda:", True, (100, 100, 100))
pygame.draw.rect(surface, (200, 50, 50), rect)

# DEPOIS
from config.settings import COR_FUNDO_HUD, COR_TEXTO_SECUNDARIO, COR_VERMELHO
surface.fill(COR_FUNDO_HUD)
font.render("Onda:", True, COR_TEXTO_SECUNDARIO)
pygame.draw.rect(surface, COR_VERMELHO, rect)
```

### 2.2 Fontes — mover para `__init__`

Se qualquer `pygame.font.SysFont()` estiver dentro de `draw()`, mover para `__init__`:

```python
class HUD:
    def __init__(self):
        self.fonte_label  = pygame.font.SysFont("monospace", 11)
        self.fonte_valor  = pygame.font.SysFont("monospace", 14, bold=True)
        self.fonte_boss   = pygame.font.SysFont("Impact", 16)
        self.fonte_timer  = pygame.font.SysFont("monospace", 13)
```

### 2.3 Validação

`python main.py` — abrir jogo, jogar onda 1, confirmar HUD visível sem erro.

---

## FASE 3 — Migrar cores em `ui/card_hand.py`

**Escopo:** apenas `ui/card_hand.py`.

**Proibido:** alterar `handle_click()`, `select()`, `deselect()`, lógica de `_card_rect()`, lógica de bloqueio por custo ou limite.

### 3.1 O que mudar

Substituir cores literais por constantes. Mover fontes para `__init__`. Cachear `pygame.Surface` de overlay da carta (fundo escurecido de carta bloqueada):

```python
class CardHand:
    def __init__(self, tower_types):
        # ...
        self.fonte_nome   = pygame.font.SysFont("monospace", 11, bold=True)
        self.fonte_stats  = pygame.font.SysFont("monospace", 10)
        self.fonte_desc   = pygame.font.SysFont("monospace", 10)
        self.fonte_custo  = pygame.font.SysFont("monospace", 14, bold=True)
        self.fonte_slots  = pygame.font.SysFont("monospace", 9)

        # Surface de overlay para carta bloqueada — criar uma vez
        self._overlay_bloqueada = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
        self._overlay_bloqueada.fill((0, 0, 0, 140))
```

### 3.2 Fundo das cartas

O fundo da carta deve ter gradiente simulado (dois retângulos, topo levemente mais claro):

```python
def _desenhar_fundo_carta(self, surface, rect, selecionada, buff_ativo):
    cor_fundo = COR_FUNDO_CARTA
    pygame.draw.rect(surface, cor_fundo, rect)
    # topo levemente mais claro (simulação de iluminação)
    topo = pygame.Rect(rect.x, rect.y, rect.width, 3)
    cor_topo = COR_BORDA_BUFF if buff_ativo else (COR_BORDA_ATIVA if selecionada else (58, 58, 22))
    pygame.draw.rect(surface, cor_topo, topo)
    # borda
    cor_borda = COR_BORDA_BUFF if buff_ativo else (COR_BORDA_ATIVA if selecionada else COR_BORDA_CARTA)
    pygame.draw.rect(surface, cor_borda, rect, 1)
```

### 3.3 Slots visuais

```python
def _desenhar_slots(self, surface, x, y, contagem, maximo=4):
    for i in range(maximo):
        slot_rect = pygame.Rect(x + i * 11, y, 8, 8)
        cor = COR_DOURADO if i < contagem else (30, 30, 14)
        pygame.draw.rect(surface, cor, slot_rect)
        pygame.draw.rect(surface, COR_BORDA_SUTIL, slot_rect, 1)
```

### 3.4 Validação

`python main.py` — confirmar 6 cartas visíveis com stats, selecionar carta, deselecionar. Tooltip aparece ao hover.

---

## FASE 4 — Migrar cores em `ui/menus.py`

**Escopo:** apenas `ui/menus.py`.

**Proibido:** alterar `handle_event()` de qualquer tela, lógica de transição de estado, criação/destruição de UIElements do pygame_gui.

### 4.1 Fontes — todas para `__init__`

Cada classe de tela (`MenuScreen`, `PauseScreen`, etc.) deve ter suas fontes no `__init__`:

```python
class MenuScreen:
    def __init__(self, manager):
        # pygame_gui buttons aqui (não mexer)
        self.fonte_titulo = pygame.font.SysFont("Impact", 56)
        self.fonte_sub    = pygame.font.SysFont("monospace", 12)
        self.fonte_versao = pygame.font.SysFont("monospace", 11)
```

### 4.2 Fundo do menu

Menu deve usar campo escurecido com linhas de yardage:

```python
def _desenhar_fundo_menu(self, surface):
    surface.fill(COR_FUNDO_TELA)
    # linhas verticais de yardage (10 divisões)
    largura = surface.get_width()
    altura = surface.get_height()
    for i in range(1, 11):
        x = int(largura * i / 11)
        linha = pygame.Surface((1, altura), pygame.SRCALPHA)
        linha.fill((255, 255, 255, 18))
        surface.blit(linha, (x, 0))
    # gradiente inferior dourado sutil
    grad = pygame.Surface((largura, altura // 2), pygame.SRCALPHA)
    grad.fill((255, 208, 64, 8))
    surface.blit(grad, (0, altura // 2))
```

### 4.3 Painéis (Pause, GameOver, Victory, Conquistas, etc.)

Todos os painéis devem seguir o mesmo template:

```python
def _desenhar_painel(self, surface, rect):
    # fundo
    pygame.draw.rect(surface, COR_FUNDO_MODAL, rect)
    # borda lateral e inferior sutil
    pygame.draw.rect(surface, COR_BORDA_MODAL, rect, 1)
    # topo dourado 3px
    topo = pygame.Rect(rect.x, rect.y, rect.width, 3)
    pygame.draw.rect(surface, COR_BORDA_MODAL_TOPO, topo)
```

### 4.4 Botões desenhados em Pygame (onde pygame_gui não é usado)

Botão primário com corte diagonal:

```python
def _desenhar_botao_primario(self, surface, rect, texto, fonte):
    # fundo dourado com clip diagonal via polígono
    pontos = [
        (rect.x + 10, rect.y),
        (rect.right, rect.y),
        (rect.right - 10, rect.bottom),
        (rect.x, rect.bottom)
    ]
    pygame.draw.polygon(surface, COR_DOURADO, pontos)
    # texto centralizado
    txt = fonte.render(texto, True, (10, 8, 0))
    surface.blit(txt, txt.get_rect(center=rect.center))
```

### 4.5 Validação

Navegar por todas as telas: menu → dificuldade → jogar → pausar → continuar → game over → menu. Sem erro.

---

## FASE 5 — Migrar `ui/intro_scene.py`

**Escopo:** apenas `ui/intro_scene.py`.

**Proibido:** alterar sequência de diálogos, lógica de typewriter, lógica de avanço por ENTER/ESC.

### 5.1 Fundo

Fundo da intro: campo escurecido idêntico ao menu (`_desenhar_fundo_menu`). Se a função já existe em `menus.py`, extrair para um módulo utilitário `ui/ui_utils.py` e importar nos dois.

### 5.2 Caixa de diálogo

```python
def _desenhar_caixa_dialogo(self, surface, fala_atual):
    # posição: largura total - 40px margem, altura 180px, 60px do fundo
    largura = surface.get_width()
    altura_caixa = 180
    y = surface.get_height() - altura_caixa - 60
    rect = pygame.Rect(20, y, largura - 40, altura_caixa)

    # fundo semi-transparente
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    bg.fill((8, 8, 6, 230))
    surface.blit(bg, rect.topleft)

    # borda branca 2px
    pygame.draw.rect(surface, COR_TEXTO_PRIMARIO, rect, 2)
    # topo colorido por personagem
    topo_cor = {
        "speed": COR_AZUL,
        "ancelotti": COR_VERMELHO,
        "labubu": COR_ROXO
    }.get(fala_atual["speaker"], COR_DOURADO)
    pygame.draw.rect(surface, topo_cor, pygame.Rect(rect.x, rect.y, rect.width, 3))
```

### 5.3 Validação

Abrir o jogo, deixar intro rodar até o fim e confirmar transição para menu.

---

## FASE 6 — Migrar overlays de posicionamento em `main.py` e `map/placement_grid.py`

**Escopo:** blocos de render do overlay em `main.py` e método `draw_path()` em `placement_grid.py`.

**Proibido:** alterar `is_placeable()`, `set_occupied()`, `pixel_to_cell()`, lógica de waypoints.

### 6.1 Cachear surfaces de overlay em `PlacementGrid.__init__`

```python
# Em PlacementGrid.__init__:
self._surface_overlay_livre = None   # criada lazy na primeira chamada
self._surface_overlay_path  = None

def _get_overlay_livre(self, size):
    if self._surface_overlay_livre is None or self._surface_overlay_livre.get_size() != size:
        s = pygame.Surface(size, pygame.SRCALPHA)
        s.fill((*COR_OVERLAY_LIVRE, ALPHA_OVERLAY_GLOBAL))
        self._surface_overlay_livre = s
    return self._surface_overlay_livre
```

### 6.2 Overlay de hover (cursor sobre o campo)

```python
# Em main.py, no bloco de render com carta selecionada:
mouse_x, mouse_y = pygame.mouse.get_pos()
# converter coordenadas de tela para render_surface
mx = int(mouse_x / scale_x)
my = int(mouse_y / scale_y)
if MAP_RECT.collidepoint(mx, my):
    placeable = grid.is_placeable(mx, my)
    cor = (*COR_OVERLAY_VALIDO, ALPHA_OVERLAY_HOVER) if placeable else (*COR_OVERLAY_INVALIDO, ALPHA_OVERLAY_HOVER)
    hover_surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
    hover_surf.fill(cor)
    # centralizar no cursor
    render_surface.blit(hover_surf, (mx - CELL_SIZE // 2, my - CELL_SIZE // 2))
```

**Nota:** se CELL_SIZE for 64 e o hover ficar muito grande visualmente após resposta do usuário na Fase 0, reduzir para raio circular:

```python
hover_surf = pygame.Surface((52, 52), pygame.SRCALPHA)
pygame.draw.circle(hover_surf, cor, (26, 26), 26)
render_surface.blit(hover_surf, (mx - 26, my - 26))
```

### 6.3 Validação

Selecionar carta → overlay verde aparece → hover em área livre → verde mais intenso → hover em path → vermelho.

---

## FASE 7 — Migrar `ui/leaderboard_screen.py` e `ui/conquistas_screen.py`

**Escopo:** apenas os dois arquivos acima.

**Proibido:** alterar lógica de fetch do Supabase, lógica de threading, lógica de UUID.

### 7.1 Template de painel compartilhado

Se ainda não existe `ui/ui_utils.py`, criar agora:

```python
# ui/ui_utils.py
import pygame
from config.settings import (
    COR_FUNDO_MODAL, COR_BORDA_MODAL, COR_BORDA_MODAL_TOPO,
    COR_DOURADO, COR_TEXTO_PRIMARIO, COR_TEXTO_SECUNDARIO
)

def desenhar_painel(surface, rect, cor_topo=None):
    """Padrão visual de painel para todos os modais do jogo"""
    pygame.draw.rect(surface, COR_FUNDO_MODAL, rect)
    pygame.draw.rect(surface, COR_BORDA_MODAL, rect, 1)
    cor = cor_topo or COR_BORDA_MODAL_TOPO
    pygame.draw.rect(surface, cor, pygame.Rect(rect.x, rect.y, rect.width, 3))

def desenhar_titulo_painel(surface, texto, fonte, rect):
    """Título dourado com glow sutil"""
    txt = fonte.render(texto.upper(), True, COR_DOURADO)
    pos = (rect.x + 20, rect.y + 14)
    surface.blit(txt, pos)

def desenhar_separador(surface, y, rect):
    """Linha separadora dentro de painel"""
    pygame.draw.line(surface, COR_BORDA_MODAL,
                     (rect.x + 1, y), (rect.right - 1, y), 1)

def desenhar_overlay_fundo(surface):
    """Overlay escuro semi-transparente para modais sobre o jogo"""
    bg = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 200))
    surface.blit(bg, (0, 0))
```

Usar `ui_utils` em `leaderboard_screen.py`, `conquistas_screen.py`, `update_screen.py`, `nome_vitoria_screen.py`.

### 7.2 Leaderboard — posições com cor

```python
CORES_POSICAO = {
    1: COR_DOURADO,
    2: (192, 192, 192),    # prata
    3: (205, 127, 50),     # bronze
}
cor = CORES_POSICAO.get(posicao, COR_TEXTO_DESATIVO)
```

### 7.3 Validação

Abrir leaderboard no menu → título visível → lista renderizada → fechar retorna ao menu.

---

## FASE 8 — Revisar `main.py` (render loop)

**Escopo:** apenas o bloco de render dentro do game loop de `main.py`. Nenhuma alteração em update, eventos, estados.

### 8.1 Confirmar ordem de camadas

```python
# ORDEM OBRIGATÓRIA — não alterar:
render_surface.fill(COR_FUNDO_TELA)          # 1. fundo
game_map.draw(render_surface)                 # 2. mapa
for torre in game_state.towers:               # 3. torres
    torre.draw(render_surface)
for proj in game_state.projectiles:           # 4. projéteis
    proj.draw(render_surface)
for inimigo in game_state.enemies:            # 5. inimigos
    inimigo.draw(render_surface)
# overlays de posicionamento (só se carta selecionada)
if game_state.selected_card is not None:      # 6. overlay posicionamento
    render_surface.blit(grid._get_overlay_livre(MAP_RECT.size), MAP_RECT.topleft)
    grid.draw_path(render_surface, time_elapsed)
    # hover cursor
card_hand.draw(render_surface, game_state.coins)  # 7. cartas
hud.draw(render_surface, ...)                      # 8. HUD
if current_screen:                                 # 9. modal ativo
    current_screen.draw(render_surface)
if DEV_MODE:                                       # 10. debug (último)
    grid.draw_debug(render_surface)
ui_manager.draw_ui(render_surface)                 # 11. pygame_gui (sempre por último)
# escalar para tela real
screen.blit(pygame.transform.scale(render_surface, screen.get_size()), (0, 0))
pygame.display.flip()
```

### 8.2 Substituir cores literais restantes

```bash
grep -n "fill(\|draw\." main.py | grep -E "\([0-9]" 
```

Cada ocorrência deve ser migrada para constante de `settings.py`.

### 8.3 Validação final

Partida completa sem crash: menu → intro → dificuldade → jogar ondas 1-3 → pausar → retomar → game over → menu.

---

## FASE 9 — Revisão final com code-reviewer

Acionar `code-reviewer` (Opus) para:

1. Confirmar que nenhuma cor literal `(r, g, b)` existe fora de `settings.py`
2. Confirmar que nenhuma `pygame.Surface` é criada dentro de loops de render
3. Confirmar que nenhuma fonte é instanciada fora de `__init__`
4. Confirmar que a ordem de camadas em `main.py` está correta
5. Confirmar que nenhum sistema lógico foi alterado

Gerar relatório com:
- Lista de arquivos modificados
- Contagem de cores migradas para `settings.py`
- Resultado de `python main.py` e `python main.py --dev`
- Qualquer desvio encontrado

Somente após aprovação do relatório: commitar e criar tag.

---

## REGRAS ABSOLUTAS (nunca violar)

1. **Nunca criar `pygame.Surface` dentro de `draw()` ou `update()`** — sempre cachear em `__init__` ou como atributo de classe
2. **Nunca instanciar `pygame.font` fora de `__init__`**
3. **Nunca alterar `handle_event()`, `update()`, ou qualquer método que não seja `draw()` ou `__init__`** — exceto para mover fontes/surfaces para `__init__`
4. **Nunca alterar `config/settings.py` exceto para adicionar constantes de cor**
5. **Nunca alterar `core/`, `entities/`, `map/placement_grid.py` (lógica)** — apenas `map/game_map.py` para cor do fundo do campo
6. **Nunca commitar sem relatório aprovado**
7. **Parar e perguntar** se qualquer edição exigir mudar a assinatura de um método

---

## Critério final de aprovação

- [ ] `python main.py` sem erro do início ao fim de uma partida
- [ ] `python main.py --dev` sem erro
- [ ] Nenhuma cor literal fora de `settings.py`
- [ ] Nenhuma Surface criada em loop
- [ ] Nenhuma fonte criada em draw
- [ ] UI visualmente consistente com a paleta do campo do Hard Rock Stadium
- [ ] Nenhum sistema de lógica alterado
