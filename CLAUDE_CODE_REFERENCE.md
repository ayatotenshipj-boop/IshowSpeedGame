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
| `architect-reviewer` | Opus | Antes de qualquer mudança que afete múltiplos arquivos. Decisões de arquitetura, novos sistemas, balanceamento |
| `code-reviewer` | Opus | Após concluir cada fase ou bloco. Revisão de qualidade, sintaxe, lógica |
| `debugger` | Sonnet | Quando `python main.py` falhar. Bug hunting cirúrgico |
| `security-auditor` | Opus | Antes de publicar release. Revisar updater, Supabase, chaves expostas |

**Como acionar:**
```
Use o agente architect-reviewer para analisar X antes de implementar
Use o agente code-reviewer para revisar os arquivos alterados nesta fase
Use o agente debugger para identificar a causa do erro em Y
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

**Skills do projeto (pasta `skills/`):**
- `skills/pygame-ui-adapter/SKILL.md` — adaptação visual sem quebrar lógica

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
1. /plan                          → mostrar o que vai fazer antes de codar
2. Acionar architect-reviewer     → validar abordagem
3. Implementar bloco por bloco    → um arquivo de cada vez
4. python main.py após cada fase  → nunca avançar com erro aberto
5. /compact se contexto ficar longo
6. code-reviewer ao concluir      → revisão final
7. git add + commit + push        → só após aprovação
8. tag + release se for versão    → GitHub Actions compila automaticamente
```

---

## Arquivos críticos para não perder de vista

| Arquivo | Função |
|---------|--------|
| `CLAUDE.md` | Regras absolutas do projeto — ler sempre primeiro |
| `ARCHITECTURE.md` | Camadas, módulos, responsabilidades |
| `PLAN.md` | Etapas originais (referência histórica) |
| `FIXES_AND_IMPROVEMENTS.md` | Bugs conhecidos e melhorias planejadas |
| `BUGFIX_CHANGELOG_1.md` | Primeira changelog de correções |
| `REFINAMENTOS_V1.2.0.md` | Balanceamento e novas mecânicas |
| `AJUSTES_V1.2.1.md` | Ajustes pós-refinamento |
| `UI_VISUAL_ADAPTATION.md` | Guia de adaptação visual da UI |
| `skills/pygame-ui-adapter/SKILL.md` | Skill de UI para este projeto |
| `config/settings.py` | Constantes globais — paleta, resolução, economia |
| `config/path.json` | Waypoints do caminho dos inimigos |
| `version.json` | Versão local do jogo (auto-update) |
| `.github/workflows/build.yml` | CI/CD de build Linux + Windows |
