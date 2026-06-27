# AJUSTES_V1.2.1.md
# Speed Vs Labubu Remake — Ajustes Pós-Refinamento

## Instruções Obrigatórias

**Antes de qualquer ação:**
1. Acione `architect-reviewer` (Opus) — análise de impacto dos modos de dificuldade e sistema de conquistas
2. Acione `debugger` (Sonnet) — validação do Skip Wave, UI overlap e economia
3. Skills: `systematic-debugging`, `verification-before-completion`, `karpathy-guidelines`, `full-output-enforcement`, `5-whys`
4. Plan Mode (`/plan`) — listar TODOS os arquivos afetados antes de implementar
5. NÃO commitar — aguardar aprovação do relatório final

---

## BLOCO 1 — Análise de Economia e Rebalanceamento

**Tarefa do architect-reviewer:** antes de alterar qualquer valor, analisar o fluxo econômico completo:

1. Calcular moedas ganhas por wave completa (soma de `enemy.reward * count` de cada onda em `WAVES`)
2. Calcular custo mínimo de defesa viável por wave (quantas torres mínimas para sobreviver)
3. Identificar em qual wave o jogador fica sem moedas para comprar torres
4. Reportar análise antes de propor valores

**Após análise, aplicar os seguintes ajustes:**

Moedas iniciais: `INITIAL_COINS = 400` (era 150)

Recompensas dos Labubus (ajustar para economia justa):
```python
Labubu1 — reward = 15   # era 10
Labubu2 — reward = 30   # era 20
Labubu3 — reward = 50   # era 35
Labubu4 — reward = 45   # era 30
Ancelotti — reward = 300  # era 200
LabubuMUI — reward = 8   # já existente
```

Buff de 5% em todos os Speeds (aplicar sobre os valores atuais pós-v1.2.0):
- `damage *= 1.05` (arredondar para int)
- `fire_rate *= 1.05`
- Aplicar em: Shake It Speed, Suprised Speed, SayWallahi Speed, ShockedSpeed
- NÃO aplicar em KindaHomeless Speed (suporte) e KillThatBoy (utility)

KindaHomeless Speed: `cost = 1500` (era 95)

Reportar tabela completa de economia por wave após ajustes.

---

## BLOCO 2 — Renomear Speed5 para ShockedSpeed

Em `entities/tower.py`, classe Speed5:
```python
name = "ShockedSpeed"
description = "Versátil. Buff dobra dano por 5s (CD: 15s)."
```

Atualizar em todo lugar que referencia "Speed5" por nome de exibição.

---

## BLOCO 3 — Fix do Skip Wave

**Bug atual:** Skip Wave reinicia contador mas não limpa inimigos da wave atual nem avança corretamente.

**Comportamento correto:**
1. Ao clicar Skip: remover TODOS os inimigos ativos de `game_state.enemies`
2. Remover TODOS os projéteis de `game_state.projectiles`
3. Dar bônus de moedas: `bonus = sum(e.reward for e in game_state.enemies) // 4` (calcular ANTES de limpar)
4. Forçar `wave_manager` para avançar para a próxima wave imediatamente:
   - `wave_manager.spawn_queue = []`
   - `wave_manager.wave_timer = 0.0`
   - `wave_manager.wave_active = False`
   - `wave_manager.current_wave += 1` (se não for a última)
5. Resetar `game_state.skip_timer = 0.0` e `game_state.skip_disponivel = False`
6. Auto-Skip segue o mesmo fluxo

Verificar que waves somam corretamente (onda 3 → skip → vai para onda 4, não reinicia para onda 1).

---

## BLOCO 4 — Textos das Cartas (CardHand)

**Problema:** nomes longos como "KindaHomeless Speed" e "SayWallahi Speed" transbordam a área da carta.

**Solução:**
- Detectar tamanho do texto antes de renderizar: `font.size(nome)[0]`
- Se largura do texto > largura da carta - 8px: reduzir tamanho da fonte progressivamente até caber (mínimo 8px)
- Alternativamente: truncar com reticências `"KindaHomel..."` se fonte mínima ainda não couber
- Aplicar para: nome da carta, descrição e stats no tooltip
- Garantir que tooltip não sai da tela (checar bordas antes de renderizar)

Implementar método auxiliar em `ui/card_hand.py`:
```python
def _render_texto_ajustado(self, surface, texto, rect, cor, font_max=13, font_min=8):
    """Renderiza texto reduzindo fonte até caber no rect"""
    for tamanho in range(font_max, font_min - 1, -1):
        font = pygame.font.SysFont("monospace", tamanho)
        if font.size(texto)[0] <= rect.width - 4:
            surface.blit(font.render(texto, True, cor), (rect.x + 2, rect.y + 2))
            return
    # truncar se ainda não coube
    truncado = texto[:10] + "..."
    font = pygame.font.SysFont("monospace", font_min)
    surface.blit(font.render(truncado, True, cor), (rect.x + 2, rect.y + 2))
```

---

## BLOCO 5 — Modos de Dificuldade

### 5.1 Três modos: Fácil, Normal, Difícil

Adicionar em `config/settings.py`:
```python
MODOS_DIFICULDADE = {
    "facil": {
        "nome": "Fácil",
        "hp_mult": 0.7,        # Labubus com 70% do HP
        "speed_mult": 0.8,     # 20% mais lentos
        "reward_mult": 1.3,    # 30% mais moedas
        "lives": 15,           # mais vidas
        "descricao": "Para quem está conhecendo o jogo"
    },
    "normal": {
        "nome": "Normal",
        "hp_mult": 1.0,
        "speed_mult": 1.0,
        "reward_mult": 1.0,
        "lives": 10,
        "descricao": "A experiência balanceada"
    },
    "dificil": {
        "nome": "Difícil",
        "hp_mult": 1.5,        # Labubus com 150% do HP
        "speed_mult": 1.2,     # 20% mais rápidos
        "reward_mult": 0.7,    # 30% menos moedas
        "lives": 6,            # poucas vidas
        "descricao": "Para quem domina o jogo"
    }
}
```

Adicionar em `core/game_state.py`:
```python
modo_dificuldade: str = "normal"
```

### 5.2 Tela de seleção de modo antes do jogo

Novo estado `GameScreen.SELECAO_MODO` em `state_manager.py`.

Ao clicar "JOGAR" no menu → ir para `SELECAO_MODO` antes de `PLAYING`.

`ui/modo_screen.py` — tela de seleção:
```
┌──────────────────────────────────┐
│      SELECIONE A DIFICULDADE     │
│                                  │
│  [ FÁCIL ]   Para iniciantes     │
│  [ NORMAL ]  Experiência padrão  │
│  [ DIFÍCIL ] Para veteranos      │
│                                  │
│  [ VOLTAR ]                      │
└──────────────────────────────────┘
```

Ao selecionar modo: salvar em `game_state.modo_dificuldade`, chamar `reset_game()`, iniciar jogo.

### 5.3 Aplicar multiplicadores no WaveManager

Em `entities/wave_manager.py`, ao instanciar inimigo:
```python
from config.settings import MODOS_DIFICULDADE

def _criar_inimigo(self, tipo: str, modo: str) -> Enemy:
    mult = MODOS_DIFICULDADE[modo]
    enemy = ENEMY_TYPES[tipo]()
    # HP base × multiplicador de wave × multiplicador de dificuldade
    wave_mult = 1.0 + (self.current_wave * 0.10)
    enemy.max_hp = int(enemy.max_hp * wave_mult * mult["hp_mult"])
    enemy.hp = enemy.max_hp
    enemy.speed = enemy.speed * mult["speed_mult"]
    enemy.reward = int(enemy.reward * mult["reward_mult"])
    return enemy
```

Passar `game_state.modo_dificuldade` para `wave_manager.update()`.

---

## BLOCO 6 — Sistema de Conquistas

### 6.1 `core/conquistas.py`

```python
import json
from pathlib import Path
import sys

CONQUISTAS_DEF = {
    "vitoria_facil": {
        "nome": "Treino Completo",
        "descricao": "Zerou o jogo no modo Fácil",
        "icone": "🥉",
        "desbloqueada": False
    },
    "vitoria_normal": {
        "nome": "Campeão de Miami",
        "descricao": "Zerou o jogo no modo Normal",
        "icone": "🏆",
        "desbloqueada": False
        # esta é a conquista/recompensa atual de vitória
    },
    "vitoria_dificil": {
        "nome": "Lenda do Speed",
        "descricao": "Zerou o jogo no modo Difícil",
        "icone": "💀",
        "desbloqueada": False
    }
}

def _get_path() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "speedvslabubu"
    else:
        base = Path.home() / ".config" / "speedvslabubu"
    base.mkdir(parents=True, exist_ok=True)
    return base / "conquistas.json"

def carregar() -> dict:
    path = _get_path()
    if not path.exists():
        return {k: False for k in CONQUISTAS_DEF}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {k: False for k in CONQUISTAS_DEF}

def salvar(estado: dict):
    try:
        _get_path().write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        import logging
        logging.warning("Não foi possível salvar conquistas: %s", e)

def desbloquear(conquista_id: str) -> bool:
    """Retorna True se foi desbloqueada agora (novidade), False se já tinha"""
    estado = carregar()
    if estado.get(conquista_id):
        return False
    estado[conquista_id] = True
    salvar(estado)
    return True

def get_todas() -> list[dict]:
    estado = carregar()
    resultado = []
    for cid, cdef in CONQUISTAS_DEF.items():
        resultado.append({
            **cdef,
            "id": cid,
            "desbloqueada": estado.get(cid, False)
        })
    return resultado
```

### 6.2 Integração na tela de vitória

Em `main.py`, quando vitória:
```python
from core import conquistas

modo = game_state.modo_dificuldade
conquista_id = f"vitoria_{modo}"
nova_conquista = conquistas.desbloquear(conquista_id)

# passar para VictoryScreen se foi nova conquista
current_screen = VictoryScreen(
    ui_manager,
    game_state.kills,
    game_state.coins,
    tempo=game_state.tempo_vitoria,
    nova_conquista=CONQUISTAS_DEF.get(conquista_id) if nova_conquista else None
)
```

`VictoryScreen` exibe banner especial se `nova_conquista` não é None:
```
🏆 CONQUISTA DESBLOQUEADA!
"Campeão de Miami"
Zerou o jogo no modo Normal
```

### 6.3 Tela de Conquistas no menu

`ui/conquistas_screen.py` — painel com as 3 conquistas:

Cada conquista exibe:
- Ícone + nome em dourado se desbloqueada
- Ícone cinza + "???" se bloqueada (não revelar nome)
- Descrição abaixo do nome se desbloqueada

Botão "CONQUISTAS" no menu principal já existe (estava como "Em breve...") — conectar agora a esta tela real.

---

## BLOCO 7 — Fix de UI Overlapping

**Diagnóstico obrigatório antes de corrigir:**

Com agente `debugger`, mapear todas as regiões de UI e verificar sobreposições:

1. `MAP_RECT` (0, 0, 1280, 620) — área do jogo
2. `HUD_RECT` (0, 620, 1280, 100) — barra inferior com cartas
3. Barra superior de stats (coins, lives, wave, timer) — dentro de MAP_RECT ou sobreposta?
4. Botão 2x speed — posição atual?
5. Botão Skip Wave — posição atual e colide com o quê?
6. Botão Auto-Skip — posição?
7. Botão [LOG] changelog — canto superior direito, colide com stats?
8. Tooltip das cartas — sai da tela em cartas das extremidades?
9. Cronômetro MM:SS — canto superior direito, colide com [LOG]?
10. "!! BOSS !!" piscante na onda 15 — onde está?

**Após diagnóstico, reorganizar:**

Proposta de layout sem sobreposição:
```
┌─────────────────────────────────────────────────────────────────┐
│ $400  Mortes:12  Onda:3/15  MM:SS   [2x] [SKIP +$45] [AUTO] [LOG]│  ← barra sup 30px
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    MAP_RECT (campo)                             │  ← 590px
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ❤️ 10   [carta1][carta2][carta3][carta4][carta5][carta6][carta7]│  ← HUD 100px
└─────────────────────────────────────────────────────────────────┘
```

Ajustar `MAP_RECT` para `pygame.Rect(0, 30, 1280, 590)` se necessário para acomodar barra superior.

Garantir que tooltip de carta sempre aparece ACIMA da carta e nunca sai pela borda superior.

---

## ORDEM DE IMPLEMENTAÇÃO

```
1 (economia + buff 5%) → 2 (rename ShockedSpeed) → 3 (fix skip wave)
→ 4 (textos cartas) → 7 (diagnóstico UI)
→ 5 (modos dificuldade) → 6 (conquistas)
→ 7 (fix UI após diagnóstico) → validação completa
```

---

## VALIDAÇÃO OBRIGATÓRIA

- `python main.py` abre sem erro após cada bloco
- Moedas iniciam em 400
- KindaHomeless Speed custa 1500
- Buff de 5% aplicado nos 4 Speeds corretos
- Skip Wave avança para wave seguinte e limpa inimigos
- Nomes longos cabem nas cartas sem transbordar
- Tela de seleção de dificuldade aparece ao clicar Jogar
- Multiplicadores de HP/speed/reward corretos em cada modo
- Conquista desbloqueada ao zerar cada modo
- Banner de conquista aparece na tela de vitória quando novo
- Nenhuma UI sobreposta ou fora da tela
- Tela de Conquistas no menu exibe estado real das conquistas

NÃO commitar — aguardar aprovação do relatório.
