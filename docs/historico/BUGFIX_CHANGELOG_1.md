# BUGFIX_CHANGELOG_1.md
# Speed Vs Labubu Remake — Primeira Changelog de Correções

## Instruções Obrigatórias para o Claude Code

**Antes de qualquer ação:**
1. Acione o agente `architect-reviewer` (Opus) para análise dos bugs de banco de dados e arquitetura
2. Acione o agente `debugger` (Sonnet) para análise cirúrgica de cada bug individualmente
3. Use a skill `systematic-debugging` em CADA bug — identificar raiz, confirmar falha, corrigir, testar
4. Use a skill `verification-before-completion` — cada bug deve ter confirmação de fix antes de passar ao próximo
5. Use a skill `5-whys` nos bugs de banco de dados e hitbox — entender por que o problema existe antes de corrigir
6. Use a skill `karpathy-guidelines` — soluções simples e diretas, sem over-engineering
7. Use a skill `full-output-enforcement` — nenhum arquivo truncado
8. Ao final, acione `code-reviewer` (Opus) para revisão geral

**Ordem de implementação:** banco de dados primeiro (bugs 1 e 2), depois gameplay (3-8), depois busca autônoma de bugs adicionais.

---

## BUG 1 — Data/Hora usando relógio local do PC

**Sintoma:** jogadores com VPN ou fuso diferente registram datas erradas no leaderboard. Um jogador com VPN americana aparece com data do dia anterior no Supabase.

**Raiz técnica:** `core/leaderboard.py` usa `time.strftime("%d/%m/%Y")` que lê o relógio local do sistema operacional, sem conversão de fuso horário.

**Correção:**
- Substituir `time.strftime()` por chamada à API do Supabase que já registra `created_at` com timezone UTC automaticamente
- Para exibição no leaderboard, usar o campo `created_at` do Supabase convertido para horário de Brasília (UTC-3) via `datetime` stdlib
- Remover o campo `data` manual — deixar o Supabase gerar via `DEFAULT now()`
- Exibir no leaderboard: `created_at` formatado como `dd/mm/aaaa` no fuso `America/Sao_Paulo`

```python
from datetime import datetime, timezone, timedelta

def _formatar_data_utc(created_at_str: str) -> str:
    """Converte UTC do Supabase para horário de Brasília"""
    dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    brasilia = timezone(timedelta(hours=-3))
    dt_br = dt.astimezone(brasilia)
    return dt_br.strftime("%d/%m/%Y")
```

Atualizar tabela no Supabase — remover coluna `data` manual e usar `created_at` que já existe com `DEFAULT now()`.

---

## BUG 2 — Múltiplos registros por jogador no leaderboard (CRÍTICO)

**Sintoma:** ao completar o jogo várias vezes ou reabrir o jogo, o jogador pode registrar nomes diferentes e lotar o banco de dados com entradas falsas.

**Raiz técnica:** não há identificação única por jogador. Qualquer string como nome cria uma nova linha.

**Correção — UUID fixo por instalação:**

1. Na primeira execução, gerar UUID único e salvar em arquivo local:
   - Linux: `~/.config/speedvslabubu/player_id`
   - Windows: `%APPDATA%/speedvslabubu/player_id`
   - Se o arquivo não existir: gerar com `uuid.uuid4()` e salvar
   - Se existir: carregar o UUID salvo

2. Adicionar coluna `player_id` (text) na tabela do Supabase como UNIQUE:
```sql
ALTER TABLE public.leaderboard ADD COLUMN player_id text;
ALTER TABLE public.leaderboard ADD CONSTRAINT leaderboard_player_id_unique UNIQUE (player_id);
```

3. Ao registrar vitória: usar `INSERT ... ON CONFLICT (player_id) DO UPDATE`:
```python
# endpoint com upsert
headers["Prefer"] = "resolution=merge-duplicates,return=representation"
# body inclui player_id
entrada = {
    "nome": nome,
    "tempo": tempo,
    "player_id": _get_or_create_player_id()
}
# POST com on_conflict=player_id no endpoint
endpoint = f"{TABELA}?on_conflict=player_id"
```

4. Se o jogador já tem registro e zerou mais rápido: atualiza. Se foi mais lento: mantém o melhor tempo (lógica no `WITH CHECK` ou no código).

5. Se o jogador apagar o jogo: ganha novo UUID na reinstalação — comportamento aceitável para jogo indie.

```python
import uuid
from pathlib import Path
import sys

def _get_player_id_path() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "speedvslabubu"
    else:
        base = Path.home() / ".config" / "speedvslabubu"
    base.mkdir(parents=True, exist_ok=True)
    return base / "player_id"

def _get_or_create_player_id() -> str:
    path = _get_player_id_path()
    if path.exists():
        return path.read_text().strip()
    player_id = str(uuid.uuid4())
    path.write_text(player_id)
    return player_id
```

---

## BUG 3 — Leaderboard sem limite de 10 no banco (apenas na exibição)

**Sintoma:** o banco acumula entradas ilimitadas. O `limit=10` no SELECT é só visual — os dados continuam crescendo no Supabase indefinidamente.

**Raiz técnica:** nenhuma lógica de limpeza no servidor. A query `?limit=10` só filtra na exibição.

**Correção:**
- Criar função no Supabase via SQL Editor que remove entradas além do top 10 após cada INSERT:

```sql
CREATE OR REPLACE FUNCTION limpar_leaderboard()
RETURNS TRIGGER AS $$
BEGIN
  DELETE FROM leaderboard
  WHERE player_id NOT IN (
    SELECT player_id FROM leaderboard
    ORDER BY tempo ASC
    LIMIT 10
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_limpar_leaderboard
AFTER INSERT OR UPDATE ON leaderboard
FOR EACH ROW EXECUTE FUNCTION limpar_leaderboard();
```

Isso garante que o banco nunca tem mais de 10 entradas, independente de quantos jogadores registrem.

---

## BUG 4 — Hitbox de cartas na CardHand não detecta clique

**Sintoma:** clicar em algumas cartas não abre tooltip/upgrade, o jogo não responde.

**Raiz técnica:** `ui/card_hand.py` usa `pygame.Rect` para detecção de clique, mas se as cartas foram redesenhadas com layout diferente (7 cartas, largura dinâmica), os rects podem não estar sendo recalculados corretamente após redimensionamento de janela ou mudança no número de cartas.

**Diagnóstico:**
- Adicionar modo debug temporário: desenhar `pygame.draw.rect(surface, (255,0,0), card_rect, 2)` em cada carta para visualizar os rects reais
- Comparar posição visual da carta com o rect de clique
- Verificar se `handle_click()` recalcula posições baseado no tamanho atual de `HUD_RECT` ou usa valores fixos do `__init__`

**Correção:**
- `handle_click(pos)` deve recalcular os rects das cartas dinamicamente a cada chamada, não usar cache do `__init__`
- Garantir que o cálculo de posição X de cada carta em `draw()` e em `handle_click()` usam a mesma fórmula
- Extrair método `_card_rect(index: int) -> pygame.Rect` usado tanto no draw quanto no click

---

## BUG 5 — Speed7 pode ser vendido e reimplantado infinitamente

**Sintoma:** jogador vende Speed7, reimplanta, usa hitkill novamente — bypassa o cooldown e o limite de uso único.

**Raiz técnica:** `ability_used` é instância da torre. Ao vender e reimplantar, uma nova instância é criada com `ability_used=False`.

**Correção:**
- Adicionar flag global em `GameState`: `speed7_ability_used: bool = False`
- Quando Speed7 usar habilidade: setar `game_state.speed7_ability_used = True`
- Speed7 não pode ser vendida: remover Speed7 da lista de torres vendáveis. Se sistema de venda existir, checar `isinstance(torre, Speed7)` e bloquear com mensagem "Speed7 não pode ser removido"
- Cooldown de 60s: adicionar `speed7_cooldown: float = 0.0` em `GameState`. Após usar, setar `speed7_cooldown = 60.0`. Decrementar por `dt` no update. Só permite usar novamente quando `speed7_cooldown <= 0` E `not speed7_ability_used` — mas como `ability_used` é permanente por partida, na prática só usa uma vez
- Exibir cooldown visual na carta Speed7 na CardHand: barra de progresso de 60s

Incluir no `reset_game()`: `speed7_ability_used = False`, `speed7_cooldown = 0.0`

---

## BUG 6 — Início e fim da trilha dos Labubus fora da área visível

**Sintoma:** inimigos aparecem tarde (saindo do nada) e somem antes do fim visível do campo. A trilha começa e termina além dos limites da `MAP_RECT`.

**Raiz técnica:** o crop/zoom do mapa (`CROP_LEFT=0.22`, `CROP_RIGHT=0.78`) cortou as extremidades do campo, mas os waypoints do `path.json` ainda usam coordenadas antigas que saíam pelas bordas originais da imagem completa.

**Correção:**
- O primeiro waypoint deve ter `x` igual a `MAP_RECT.left + margem_minima` (ex: 10px)
- O último waypoint deve ter `x` igual a `MAP_RECT.right - margem_minima` (ex: 10px)
- Ajustar `config/path.json` para que início e fim estejam dentro dos limites visíveis
- Verificar em modo `--dev` com grid visível que o path começa e termina dentro da tela
- Inimigos spawnam no primeiro waypoint — garantir que esse ponto é visível na tela

---

## BUG 7 — Quadrado verde ao posicionar Speed (deve ser área livre total)

**Sintoma:** ao selecionar carta, aparece um quadrado/célula verde destacando onde pode posicionar. Deve mostrar a área inteira disponível, não um quadrado específico.

**Raiz técnica:** `main.py` ainda renderiza highlight de célula individual (`cell_rect`) no cursor, além do overlay global verde/vermelho.

**Correção:**
- Remover completamente o highlight de célula individual no cursor
- Manter apenas os dois overlays globais:
  - Verde semi-transparente cobrindo toda a `MAP_RECT` exceto o path
  - Vermelho sobre o path (trilha dos inimigos)
- Hitbox de cada Speed: círculo com raio fixo idêntico para todos os tipos — `HIT_RADIUS = 26` pixels (independente do tipo de Speed)
- Verificação de sobreposição: distância euclidiana entre centros > `HIT_RADIUS * 2`
- Remover qualquer referência a `cell_rect`, `highlight_cell`, ou `draw_rect` no cursor durante posicionamento

---

## BUG 8 — 2x Speed não acelera o tempo de partida

**Sintoma:** o botão 2x existe mas uma partida em 2x demora o mesmo tempo que em 1x. O multiplicador não está sendo aplicado corretamente.

**Raiz técnica:** `game_state.speed_multiplier` existe mas provavelmente não está sendo aplicado em TODOS os sistemas que dependem de tempo. Lista completa do que precisa usar `dt * speed_multiplier`:

- `enemy.update(dt)` → movimento dos inimigos
- `wave_manager.update(dt)` → timers de spawn e intervalo entre ondas
- `tower.update(dt)` → `fire_timer` das torres
- `projectile.update(dt)` → movimento dos projéteis
- `boss.update(dt)` → movimento e spawn_timer do Ancelotti
- Todos os `death_flashes` timers
- `slow_timer` dos inimigos afetados por Speed4
- `buff_timer` e `cooldown_timer` do Speed6
- `speed7_cooldown` em GameState
- Timers de efeitos visuais (flash de célula inválida, etc.)

**Correção:**
- Em `main.py`, definir `dt_jogo = dt * game_state.speed_multiplier` logo no início do bloco de update
- Substituir TODOS os `dt` dentro do bloco de update por `dt_jogo`
- O `dt` original (sem multiplicador) continua sendo usado apenas para: `ui_manager.update(dt)`, timers de UI, áudio
- O cronômetro de speedrun deve usar tempo real (`time.time()`), não `dt` acumulado — já está correto se usar `time.time() - tempo_inicio`

---

## BUSCA AUTÔNOMA DE BUGS ADICIONAIS

Após corrigir os 8 bugs acima, executar análise autônoma:

**Com agente `debugger` (Sonnet) + skill `systematic-debugging`:**

1. Rodar `python main.py` e jogar uma partida completa das ondas 1-15 sem interrupção — registrar qualquer comportamento inesperado

2. Testar casos extremos:
   - Posicionar 4 Speed7 (deve bloquear na 5ª)
   - Usar Skip em todas as ondas consecutivamente
   - Ativar 2x speed durante spawn de boss
   - Abrir leaderboard imediatamente após iniciar o jogo (antes de qualquer conexão)
   - Fechar e reabrir o jogo após vitória — confirmar que UUID é o mesmo
   - Tentar registrar nome vazio no leaderboard

3. Verificar memory leaks: `death_flashes`, `projectiles` e `enemies` sendo limpos corretamente em todos os cenários de remoção

4. Verificar que `reset_game()` realmente zera TODOS os campos — comparar com lista completa de campos em `GameState`

5. Verificar comportamento de áudio em edge cases: Speed7 ativado quando `sound.mp3` não está tocando, crossfade interrompido por `reset_game()`

---

## AO FINAL — Push e Release

Após todas as correções validadas:

```bash
git add .
git commit -m "fix: changelog 1 - banco de dados, hitbox, speed7, trilha, 2x speed"
git push
git tag -a v1.1.0 -m "v1.1.0 - Primeira changelog de correções"
git push origin v1.1.0
```

O GitHub Actions compila Linux e Windows automaticamente.

Atualizar `version.json` com `"version": "1.1.0"` e `download_url` apontando para os novos executáveis da Release v1.1.0.

---

## COMANDOS SQL PARA EXECUTAR NO SUPABASE ANTES DE COMEÇAR

Abrir SQL Editor do Supabase e rodar em sequência:

```sql
-- 1. Adicionar player_id único
ALTER TABLE public.leaderboard ADD COLUMN IF NOT EXISTS player_id text;
ALTER TABLE public.leaderboard ADD CONSTRAINT IF NOT EXISTS leaderboard_player_id_unique UNIQUE (player_id);

-- 2. Remover coluna data manual (usar created_at do Supabase)
ALTER TABLE public.leaderboard DROP COLUMN IF EXISTS data;

-- 3. Trigger de limpeza automática top 10
CREATE OR REPLACE FUNCTION limpar_leaderboard()
RETURNS TRIGGER AS $$
BEGIN
  DELETE FROM leaderboard
  WHERE player_id NOT IN (
    SELECT player_id FROM leaderboard
    ORDER BY tempo ASC
    LIMIT 10
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_limpar_leaderboard ON leaderboard;
CREATE TRIGGER trigger_limpar_leaderboard
AFTER INSERT OR UPDATE ON leaderboard
FOR EACH ROW EXECUTE FUNCTION limpar_leaderboard();

-- 4. Grant para função
GRANT EXECUTE ON FUNCTION limpar_leaderboard() TO anon;
```
