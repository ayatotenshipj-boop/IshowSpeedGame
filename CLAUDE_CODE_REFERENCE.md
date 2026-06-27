# CLAUDE_CODE_REFERENCE.md
# Speed Vs Labubu Remake — Skills, Agentes e Comandos de Referência

## Tabela de Problemas → Solução

| Problema | Solução |
|----------|---------|
| Código verboso ou redundante | `/simplify` (built-in) |
| Bug de lógica | `/diff` + `/review` (built-in) ou agente `code-reviewer` |
| Claude perdeu o contexto do projeto | Subagente por tarefa via `Task()` com contexto isolado |
| Resolveu o problema errado | `/plan` antes de codar + `/compact` entre blocos |

---

## Agentes disponíveis no projeto

| Agente | Modelo | Quando usar |
|--------|--------|-------------|
| `architect-reviewer` | Opus | Mudanças ≥3 arquivos, decisões de design, balanceamento, novos sistemas |
| `code-reviewer` | Opus | Revisão profunda ao fechar uma fase; antes de release |
| `debugger` | Sonnet | Quando `python main.py` falhar. Bug hunting cirúrgico |
| `security-auditor` | Opus | Somente antes de publicar release (updater, Supabase, chaves) |
| `cavecrew-builder` | built-in¹ | Edição cirúrgica 1-2 arquivos; recusa escopo ≥3 |
| `cavecrew-investigator` | built-in¹ | Localizar símbolo/definição pontual (~60% menos tokens que Explore) |
| `cavecrew-reviewer` | built-in¹ | Revisão terse de diff; `path:line: severidade: problema. fix.` |

¹ Agentes do plugin Caveman — gerenciados pelo harness, sem modelo fixo.

**Como acionar:**
```
Use o agente architect-reviewer para analisar X antes de implementar
Use o agente code-reviewer para revisar os arquivos alterados nesta fase
Use o agente debugger para identificar a causa do erro em Y
Use o agente cavecrew-reviewer para revisar o diff do bloco atual
```

---

## Skills obrigatórias neste projeto

Nunca iniciar uma sessão de trabalho sem ativar estas:

| Skill | Quando usar |
|-------|-------------|
| `full-output-enforcement` | Sempre — garante que nenhum arquivo seja entregue truncado |
| `verification-before-completion` | Sempre — valida cada critério antes de marcar como concluído |
| `systematic-debugging` | Sempre que houver bug — diagnóstico antes de tentar fix |
| `karpathy-guidelines` | Sempre — sem over-engineering, solução mais simples que funciona |
| `5-whys` | Bugs de banco de dados, lógica de jogo, problemas recorrentes |
| `writing-plans` | Antes de qualquer bloco novo — documentar antes de implementar |
| `pygame-ui-adapter` | Qualquer edição visual no Pygame — paleta, fontes, surfaces |

**Skill do projeto (raiz do projeto):**
- `pygame-ui-adapter-SKILL.md` — adaptação visual sem quebrar lógica

---

## Comandos do Claude Code usados com frequência

### Controle de sessão
```
/plan          → entrar em Plan Mode. Usar antes de qualquer implementação nova
/compact       → compactar contexto. Usar entre blocos grandes para não perder o fio
/clear         → limpar contexto completamente. Usar ao iniciar tarefa desconectada
```

### Qualidade de código
```
/review        → revisão do código atual
/diff          → ver o que mudou desde o último checkpoint
/simplify      → simplificar código verboso ou redundante
```

### Diagnóstico
```
/debug         → modo de debug ativo
```

### Git (usados ao final de cada fase aprovada)
```bash
git add .
git commit -m "tipo: descrição curta"
git push
git tag -a vX.X.X -m "descrição da versão"
git push origin vX.X.X
```

### Testes rápidos do jogo
```bash
python main.py              # modo normal
python main.py --dev        # modo dev (grid, alcance, fps, contador de entidades)
```

### Diagnóstico de UI
```bash
# Encontrar cores literais fora de settings.py
grep -rn "fill(\|draw\." ui/ main.py | grep -E "\([0-9]"

# Encontrar fontes instanciadas fora de __init__
grep -rn "SysFont\|Font(" ui/ main.py | grep -v "__init__"

# Encontrar Surfaces criadas dentro de draw/update
grep -rn "pygame.Surface" ui/ main.py
```

### Diagnóstico de banco de dados (Supabase)
```bash
# Testar conexão e INSERT/SELECT
python3 -c "
import urllib.request, json
URL = 'https://kooausbgcmhmijgqjcpd.supabase.co'
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
headers = {'apikey': KEY, 'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'}
req = urllib.request.Request(f'{URL}/rest/v1/leaderboard?select=nome,tempo&order=tempo.asc&limit=10', headers=headers)
with urllib.request.urlopen(req, timeout=5) as r:
    print(json.loads(r.read().decode()))
"
```

### PyInstaller (compilação)
```bash
# Linux
pyinstaller --onefile --windowed \
  --add-data "assets:assets" \
  --add-data "config:config" \
  --add-data "version.json:." \
  --name "SpeedVsLabubu-Linux" \
  main.py

# Windows (via GitHub Actions — não rodar local)
# Ver .github/workflows/build.yml
```

### Supabase (SQL Editor)
```sql
-- Ver registros do leaderboard
SELECT * FROM leaderboard ORDER BY tempo ASC;

-- Limpar tudo
TRUNCATE TABLE leaderboard;

-- Ver policies ativas
SELECT policyname, cmd, roles, with_check FROM pg_policies WHERE tablename = 'leaderboard';

-- Trigger de limpeza top 10
SELECT trigger_name FROM information_schema.triggers WHERE event_object_table = 'leaderboard';
```

---

## Fluxo padrão de uma sessão de trabalho

```
1. /plan + writing-plans          → escopo antes de codar
2. architect-reviewer (Opus)      → só se ≥3 arquivos ou decisão de design/balanceamento
3. cavecrew-builder               → edição cirúrgica bloco a bloco (1-2 arquivos por vez)
   └ ≥3 arquivos? volte ao plano e divida
4. python main.py após cada bloco → nunca avançar com erro aberto
5. cavecrew-reviewer              → revisão terse do diff do bloco
6. caveman-stats → /compact       → se contexto inflou por varreduras grandes
7. code-reviewer (Opus)           → revisão profunda ao fechar a fase
8. caveman-commit                 → mensagem de commit PT-BR automática
9. security-auditor               → SOMENTE antes de release
10. bump version.json + tag       → GitHub Actions compila Linux + Windows
```

## Situação → Ferramenta (referência rápida)

| Situação | Ferramenta |
|----------|-----------|
| Contexto inflou | `caveman-stats` → `/compact` |
| Antes de commitar | `caveman-commit` (PT-BR automático) |
| Revisão rápida de diff | `cavecrew-reviewer` |
| Revisão profunda de fase | `code-reviewer` (Opus) |
| Revisão de arquitetura | `architect-reviewer` (Opus) |
| Localizar onde X é definido | `cavecrew-investigator` |
| Entender subsistema inteiro | Explore agent |
| Edição cirúrgica 1-2 arquivos | `cavecrew-builder` |
| Bug hunting | `debugger` (Sonnet) + `systematic-debugging` |
| Balanceamento do jogo | `architect-reviewer` (Opus) |
| Antes de publicar release | `security-auditor` (Opus) |
| Estatísticas da sessão | `caveman-stats` |

---

## Arquivos críticos para não perder de vista

| Arquivo | Função |
|---------|--------|
| `CLAUDE.md` | Regras absolutas do projeto — ler sempre primeiro |
| `ARCHITECTURE.md` | Camadas, módulos, responsabilidades |
| `PLAN.md` | Etapas originais (referência histórica) |
| `FIXES_AND_IMPROVEMENTS.md` | Bugs conhecidos e melhorias planejadas |
| `UI_VISUAL_ADAPTATION.md` | Guia de adaptação visual da UI |
| `pygame-ui-adapter-SKILL.md` | Skill de UI para este projeto (raiz do projeto) |
| `docs/historico/` | Changelogs históricos (BUGFIX, REFINAMENTOS, AJUSTES) |
| `config/settings.py` | Constantes globais — paleta, resolução, economia |
| `config/path.json` | Waypoints do caminho dos inimigos |
| `version.json` | Versão local do jogo (auto-update) |
| `.github/workflows/build.yml` | CI/CD de build Linux + Windows |
