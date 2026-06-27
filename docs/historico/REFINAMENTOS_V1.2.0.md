# REFINAMENTOS_V1.2.0.md
# Speed Vs Labubu Remake — Refinamentos, Balanceamento e Novas Mecânicas

## Instruções Obrigatórias

**Antes de qualquer ação:**
1. Acione `architect-reviewer` (Opus) para análise do balanceamento e novas mecânicas
2. Acione `debugger` (Sonnet) para validação de cada sistema alterado
3. Skills obrigatórias: `systematic-debugging`, `verification-before-completion`, `karpathy-guidelines`, `full-output-enforcement`
4. Plan Mode (`/plan`) — listar TODOS os arquivos afetados antes de implementar
5. Não commitar até aprovação do relatório final

---

## BLOCO A — UI: Barra de Volume

### A1. Substituir botão de volume por slider arrastável

**Remover:** botão `[🔉 Diminuir Música]` atual em `ui/menus.py` → `ConfiguracoesScreen`

**Implementar:** slider padrão de volume 0–100%

Layout da tela de configurações:
```
┌─────────────────────────────────┐
│        CONFIGURAÇÕES            │
│                                 │
│  Volume da Música               │
│  [━━━━━━━━●━━━━━━━] 70%         │
│                                 │
│  [ FECHAR ]                     │
└─────────────────────────────────┘
```

Implementar slider em Pygame puro (sem pygame_gui) para controle fino:
- Trilha: retângulo 300×6px, cor cinza escuro
- Handle: círculo 16px de raio, cor dourada, arrastável com mouse
- Valor: 0.0 a 1.0 mapeado para posição X do handle
- Exibir porcentagem `"70%"` ao lado direito do slider
- `MOUSEBUTTONDOWN` sobre handle → capturar drag
- `MOUSEMOTION` com drag ativo → atualizar posição e chamar `audio.set_volume(valor)`
- `MOUSEBUTTONUP` → soltar drag

`AudioManager` já tem método de volume — conectar diretamente.

Incluir no changelog: `"- Controle de volume agora é uma barra deslizável de 0 a 100%"`

---

## BLOCO B — Renomeação dos Speeds

**Alterar `name` em cada subclasse de `entities/tower.py`:**

| Classe | Nome Antigo | Nome Novo |
|--------|-------------|-----------|
| Speed1 | Speed1 | Shake It Speed |
| Speed2 | Speed2 | Suprised Speed |
| Speed3 | Speed3 | SayWallahi Speed |
| Speed4 | Speed4 | KindaHomeless Speed |
| Speed5 | Speed5 | (manter Speed5 — ver Bloco C) |
| Speed7 | Speed7 | KillThatBoy |
| Speed8 | Speed8 | (sprite pós-habilidade, sem alteração) |

Atualizar `description` de cada um para refletir o novo nome no tooltip.
Atualizar CardHand para exibir nome novo.

Incluir no changelog: `"- Speeds renomeados para maior familiarização com o personagem"`

---

## BLOCO C — Speed5 e Speed6 unificados

### C1. Speed5 e Speed6 são a mesma carta

**Speed5** é a carta base. **Speed6 não é mais uma carta separada** — é o estado de buff do Speed5.

**Remover Speed6 da CardHand** — agora só 6 cartas jogáveis: Speed1–5 + Speed7 (KillThatBoy).

**Comportamento do Speed5 com buff:**
- Estado base: sprite `speed5.png`, stats normais
- Ao ativar buff (clicar na torre posicionada): sprite muda para `speed6.png`, dano dobra por 5s
- Após 5s: sprite volta para `speed5.png`, cooldown de 15s começa
- Durante cooldown: indicador visual na carta e na torre
- Após cooldown: buff disponível novamente

**Implementar em `entities/tower.py`:**
```python
class Speed5(Tower):
    name = "Speed5"
    # ... stats normais ...
    buff_active: bool = False
    buff_timer: float = 0.0
    buff_cooldown: float = 15.0
    cooldown_timer: float = 0.0
    
    @property
    def sprite_atual(self):
        return self._sprite_buff if self.buff_active else self._sprite_base
    
    def activate_buff(self):
        if not self.buff_active and self.cooldown_timer <= 0:
            self.buff_active = True
            self.buff_timer = 5.0
    
    def update(self, dt, enemies):
        if self.buff_active:
            self.buff_timer -= dt
            if self.buff_timer <= 0:
                self.buff_active = False
                self.cooldown_timer = self.buff_cooldown
        elif self.cooldown_timer > 0:
            self.cooldown_timer -= dt
        
        damage_efetivo = self.damage * (2 if self.buff_active else 1)
        # usar damage_efetivo ao criar Projectile
```

Incluir no changelog: `"- Speed5 agora transforma em modo buff (sprite Speed6) ao ser ativado"`

---

## BLOCO D — Skip Wave Reformulado

### D1. Novo comportamento do Skip Wave

**Remover:** botão Skip imediato atual durante intervalo entre ondas.

**Novo comportamento:**
- Skip Wave só aparece **15–20s após o início de uma wave ativa** (não no intervalo — durante a wave)
- Tempo de aparecimento: `random.uniform(15.0, 20.0)` segundos após o primeiro spawn da wave
- Valor fixo de bônus: `1/4 do total de recompensas dos Labubus restantes na wave`
- Cálculo: `bonus = sum(enemy.reward for enemy in game_state.enemies) // 4`
- Ao clicar Skip: matar todos os inimigos restantes silenciosamente (sem coins de kill), dar bônus, avançar para próxima wave
- O botão desaparece se a wave terminar naturalmente antes do jogador clicar

**Botão Auto-Skip:**
- Toggle permanente no HUD: `[AUTO]` cinza (desativo) / `[AUTO]` verde (ativo)
- Quando ativo: ao aparecer o Skip disponível, acionar automaticamente após 3s
- Persiste entre waves até o jogador desativar

**Implementar em `core/game_state.py`:**
```python
skip_timer: float = 0.0          # tempo desde início da wave atual
skip_disponivel: bool = False     # True quando 15-20s passaram
skip_threshold: float = 0.0      # valor sorteado entre 15-20s
auto_skip: bool = False           # toggle do Auto-Skip
auto_skip_timer: float = 3.0     # countdown do auto-skip quando disponível
```

Incluir no changelog: `"- Skip Wave agora aparece durante a wave com bônus de moedas"\n"- Botão Auto-Skip adicionado"`

---

## BLOCO E — Labubu4: Desaceleração Progressiva

### E1. Mecânica de cansaço do Labubu4

Após completar **4 curvas** (mudanças de direção no path), Labubu4 começa a perder velocidade:
- A cada curva completada além da 4ª: velocidade reduz 10% do valor base
- Mínimo: 30% da velocidade original (não para completamente)

**Implementar em `entities/enemy.py`:**
```python
class Labubu4(Enemy):
    # ... stats ...
    curvas_completadas: int = 0
    velocidade_base: float = 110.0  # guardar original
    
    def update(self, dt, waypoints):
        # ao atingir um waypoint (mudança de direção):
        if chegou_no_waypoint:
            self.waypoint_index += 1
            self.curvas_completadas += 1
            if self.curvas_completadas > 4:
                reducao = (self.curvas_completadas - 4) * 0.10
                self.speed = max(
                    self.velocidade_base * 0.30,
                    self.velocidade_base * (1.0 - reducao)
                )
```

Incluir no changelog: `"- Labubu4 desacelera 10% a cada curva após a 4ª"`

---

## BLOCO F — Balanceamento Completo

### F1. Filosofia de balanceamento

- Speeds early-game: baratos, dano baixo, adequados para waves 1-5
- Speeds mid-game: custo médio, especialidades, waves 6-10
- Speeds end-game: caros, alto impacto, waves 11-15
- Cada Speed tem 1 ponto forte e 1 fraqueza clara
- Labubus têm fraquezas e resistências a tipos específicos de dano

### F2. Stats dos Speeds (balanceados)

```python
# EARLY GAME
class Speed1:  # Shake It Speed — early, barato, sustentado
    cost = 50
    damage = 8
    range_px = 120
    fire_rate = 2.0      # ponto forte: cadência alta
    description = "Cadência alta. Fraco contra tanques."
    # fraqueza: dano baixo, ineficiente contra Labubu3/4

class Speed2:  # Suprised Speed — alcance, early/mid
    cost = 75
    damage = 10
    range_px = 220       # ponto forte: maior alcance
    fire_rate = 1.0
    description = "Alcance amplo. Cadência lenta."
    # fraqueza: fire_rate baixo

class Speed3:  # SayWallahi Speed — sniper, mid
    cost = 110
    damage = 45          # ponto forte: dano altíssimo
    range_px = 90
    fire_rate = 0.4
    description = "Dano massivo. Alcance curto e lento."
    # fraqueza: range curto, fire_rate muito baixo

# MID GAME
class Speed4:  # KindaHomeless Speed — suporte, mid
    cost = 95
    damage = 6
    range_px = 160
    fire_rate = 1.8
    slow = True          # ponto forte: slow 2s
    description = "Aplica lentidão. Só 1 por vez."
    # fraqueza: dano baixo, limite de 1 ativo (Ancelotti imune)
    MAX_PER_TYPE = 1     # overrride do limite padrão de 4

class Speed5:  # Speed5 — versátil, mid/end com buff
    cost = 130
    damage = 18
    range_px = 150
    fire_rate = 1.5
    description = "Versátil. Buff dobra dano por 5s (CD: 15s)."
    # ponto forte: buff ativável
    # fraqueza: cooldown longo, custo alto

# END GAME
class Speed7:  # KillThatBoy — ultimate, end
    cost = 350
    damage = 0
    range_px = 9999
    fire_rate = 0
    description = "Hitkill global. Uso único. Não vendável."
    MAX_PER_TYPE = 1
    # ponto forte: elimina tudo
    # fraqueza: uso único por partida, caríssimo
```

### F3. Propriedades dos Labubus (fraquezas e resistências)

```python
class Labubu1:  # fraco e rápido
    hp = 60
    speed = 120
    reward = 10
    # fraco para: Speed1 (cadência alta pega o rápido)
    # resistente a: nada

class Labubu2:  # médio, equilibrado
    hp = 140           # +20 das waves 1-5
    speed = 80
    reward = 20
    # fraco para: Speed3 (1 tiro quase mata)
    # resistente a: slow (não tem efeito especial)

class Labubu3:  # tanque lento
    hp = 300           # aumentado
    speed = 50
    reward = 35
    # fraco para: Speed3 + Speed5 buff (dano alto)
    # resistente a: Speed1 (dano baixo demais)

class Labubu4:  # rápido e resistente, desacelera
    hp = 220           # aumentado de 200
    speed = 110
    reward = 30
    # fraco para: Speed4 slow (cancela vantagem de velocidade)
    # resistente a: Speed3 (passa rápido demais do range curto)
```

### F4. Escala de HP por wave (+10% a cada wave)

Implementar multiplicador em `wave_manager.py`:

```python
def _hp_multiplicador(wave_index: int) -> float:
    """HP aumenta 10% por wave a partir da wave 1"""
    return 1.0 + (wave_index * 0.10)

# ao instanciar inimigo:
enemy = ENEMY_TYPES[tipo]()
enemy.max_hp = int(enemy.max_hp * _hp_multiplicador(self.current_wave))
enemy.hp = enemy.max_hp
```

Wave 1: HP base. Wave 5: HP × 1.5. Wave 10: HP × 2.0. Wave 15: HP × 2.5.

### F5. Vidas do jogador: 20 → 10

- `INITIAL_LIVES = 10` em `config/settings.py`
- Dano por inimigo que atravessa o path:
  ```
  Labubu1: -1 vida
  Labubu2: -1 vida
  Labubu3: -2 vidas
  Labubu4: -2 vidas
  Ancelotti: -5 vidas (quase game over instantâneo)
  ```
- Adicionar atributo `damage_to_base: int` em cada Enemy

### F6. Speed4 — limite de 1 por vez

Speed4 (`KindaHomeless Speed`) só pode ter 1 instância no mapa. Se tentar posicionar 2ª: bloquear com mensagem "Apenas 1 KindaHomeless Speed por vez".

Implementar via `MAX_PER_TYPE = 1` em Speed4 (mesmo sistema do MAX_PER_TYPE=4 dos outros).

---

## BLOCO G — Stun no Ancelotti + Labubu MUI

### G1. Todos os Speeds aplicam stun no Ancelotti

Ao acertar Ancelotti com qualquer projétil:
- Chance de stun: 15% por acerto
- Duração do stun: 1.5s
- Durante stun: Ancelotti para de se mover e não spawna reforços
- Efeito visual: sprite pisca amarelo durante stun

**Implementar em `entities/boss.py`:**
```python
stun_timer: float = 0.0
stun_chance: float = 0.15

def apply_stun(self, duration: float = 1.5):
    self.stun_timer = duration

def update(self, dt, waypoints):
    if self.stun_timer > 0:
        self.stun_timer -= dt
        return (False, None)  # parado durante stun
    # movimento normal...
```

**Em `main.py`**, ao acertar Ancelotti com projétil:
```python
if isinstance(proj.target, Ancelotti):
    import random
    if random.random() < proj.target.stun_chance:
        proj.target.apply_stun(1.5)
```

### G2. Labubu MUI — invocado pelo Ancelotti

Ao tomar dano (não mais por cooldown de tempo), Ancelotti tem 20% de chance de spawnar **Labubu MUI**:

```python
class LabubuMUI(Enemy):
    """50% mais fraco que os Labubus da wave atual em todos os aspectos"""
    name = "Labubu MUI"
    
    @classmethod
    def criar_para_wave(cls, wave_atual: int):
        """Cria Labubu MUI com stats 50% dos Labubus da wave mais alta disponível"""
        # determinar labubu de referência pela wave
        if wave_atual >= 12:
            ref_hp, ref_speed, ref_reward = 220, 110, 30  # Labubu4 base
        elif wave_atual >= 8:
            ref_hp, ref_speed, ref_reward = 300, 50, 35   # Labubu3 base
        elif wave_atual >= 5:
            ref_hp, ref_speed, ref_reward = 140, 80, 20   # Labubu2 base
        else:
            ref_hp, ref_speed, ref_reward = 60, 120, 10   # Labubu1 base
        
        # aplicar multiplicador de HP da wave
        mult = 1.0 + (wave_atual * 0.10)
        
        mui = cls()
        mui.max_hp = int(ref_hp * mult * 0.5)   # 50% mais fraco
        mui.hp = mui.max_hp
        mui.speed = ref_speed * 0.5
        mui.reward = max(5, int(ref_reward * 0.5))
        return mui
```

Sprite: `assets/labubus/labubu1.png` com tint vermelho (Surface colorkey) para diferenciar visualmente.

Em `boss.py`, ao tomar hit:
```python
MUI_CHANCE = 0.20

def receber_dano(self, dano: int, wave_atual: int) -> 'LabubuMUI | None':
    self.hp -= dano
    import random
    if random.random() < self.MUI_CHANCE:
        mui = LabubuMUI.criar_para_wave(wave_atual)
        mui.x, mui.y = self.x, self.y
        mui.waypoint_index = self.waypoint_index
        return mui
    return None
```

Em `main.py`, ao processar dano no Ancelotti:
```python
if isinstance(proj.target, Ancelotti):
    mui = proj.target.receber_dano(proj.damage, game_state.wave)
    if mui:
        game_state.enemies.append(mui)
```

---

## BLOCO H — Changelog Automático

Atualizar `version.json` com changelog completo desta versão:

```json
{
  "version": "1.2.0",
  "changelog": "v1.2.0 - Refinamentos e Balanceamento\n\n[UI]\n- Controle de volume agora é barra deslizável 0-100%\n\n[Speeds]\n- Speeds renomeados: Shake It Speed, Suprised Speed, SayWallahi Speed, KindaHomeless Speed, KillThatBoy\n- Speed5 e Speed6 unificados: Speed5 transforma em modo buff (sprite Speed6)\n- KindaHomeless Speed limitado a 1 por mapa\n\n[Gameplay]\n- Skip Wave aparece 15-20s após início da wave com bônus de moedas\n- Botão Auto-Skip adicionado\n- Labubu4 desacelera 10% a cada curva após a 4ª\n- Vidas do jogador reduzidas de 20 para 10\n- Dano ao base varia por tipo de Labubu\n- HP dos Labubus aumenta 10% por wave\n\n[Boss]\n- Todos os Speeds têm 15% de chance de stunnar Ancelotti por 1.5s\n- Ancelotti invoca Labubu MUI ao tomar dano (20% de chance)\n- Labubu MUI é 50% mais fraco que os Labubus da wave atual\n\n[Balanceamento]\n- Stats de todos os Speeds rebalanceados por fase do jogo\n- Fraquezas e resistências dos Labubus definidas",
  "download_url": {
    "linux": "https://github.com/ayatotenshipj-boop/IshowSpeedGame/releases/download/v1.2.0/SpeedVsLabubu-Linux",
    "windows": "https://github.com/ayatotenshipj-boop/IshowSpeedGame/releases/download/v1.2.0/SpeedVsLabubu-Windows.exe"
  },
  "files": []
}
```

---

## ORDEM DE IMPLEMENTAÇÃO

```
B (renomear speeds)
→ C (unificar Speed5/6)
→ F2 (stats balanceados)
→ F3 (propriedades Labubus)
→ F4 (escala HP por wave)
→ F5 (vidas 10, dano por tipo)
→ F6 (Speed4 limite 1)
→ E (Labubu4 desaceleração)
→ G1 (stun Ancelotti)
→ G2 (Labubu MUI)
→ D (Skip Wave reformulado)
→ A (slider volume)
→ H (version.json changelog)
→ Validação completa
```

---

## VALIDAÇÃO OBRIGATÓRIA

Após cada bloco, confirmar:
- `python main.py` abre sem erro
- Stats novos aplicados corretamente
- HP scale por wave funcionando (wave 5 tem HP × 1.5)
- Speed4 não deixa posicionar 2ª instância
- Speed5 muda sprite ao ativar buff
- Labubu4 desacelera após 4 curvas
- Stun do Ancelotti funciona (log quando ocorre)
- Labubu MUI spawna ao acertar Ancelotti
- Skip Wave aparece durante wave (não no intervalo)
- Slider de volume responde ao arrasto
- Vidas iniciam em 10
- Changelog v1.2.0 exibe corretamente na tela

Não commitar — aguardar aprovação do relatório.
