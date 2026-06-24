-- =====================================================================
-- Migração do leaderboard — Speed Vs Labubu v1.1.0
-- Cobre BUG 1 (data), BUG 2 (player_id/upsert) e BUG 3 (limite top-10).
--
-- RODE NO SQL EDITOR DO SUPABASE, EM SEQUÊNCIA. O código Python (v1.1.0) já
-- envia player_id e NÃO envia mais o campo `data` — então esta migração deve
-- ser aplicada em coordenação com o deploy do jogo:
--
--   * BUG 2/3 (ADD COLUMN player_id) → rodar ANTES de publicar o jogo novo
--     (o jogo passa a enviar player_id; sem a coluna, o INSERT falha).
--   * BUG 1 (DROP COLUMN data)       → rodar DEPOIS de publicar o jogo novo
--     (o jogo para de enviar `data`; dropar antes não quebra, mas o jogo
--      antigo ainda em uso quebraria o INSERT).
--
-- Corrige 4 erros do rascunho original do changelog:
--   1) `ADD CONSTRAINT IF NOT EXISTS` NÃO existe em Postgres → usa CREATE
--      UNIQUE INDEX IF NOT EXISTS.
--   2) Trigger top-10 com `player_id NOT IN (...)` falha silenciosamente se
--      houver player_id NULL (lógica ternária do SQL) → usa a PK (id) e
--      backfill dos legados.
--   3) UPSERT puro sobrescreve com tempo PIOR → guard "só melhora" (trigger
--      BEFORE UPDATE).
--   4) Faltam os GRANTs SELECT/INSERT/UPDATE à role `anon` (BLOQUEIO conhecido:
--      sem isso o leaderboard fica vazio mesmo com RLS).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0. Pré-requisito: created_at gerado pelo servidor (BUG 1)
--    Se a coluna já existe, este ALTER é inócuo.
-- ---------------------------------------------------------------------
ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

-- ---------------------------------------------------------------------
-- 1. BUG 2 — Identidade única por instalação
--    Coluna NULLABLE (não quebra linhas legadas) + índice único.
--    NULLs não violam UNIQUE no Postgres, então legados convivem.
-- ---------------------------------------------------------------------
ALTER TABLE public.leaderboard
  ADD COLUMN IF NOT EXISTS player_id text;

CREATE UNIQUE INDEX IF NOT EXISTS leaderboard_player_id_unique
  ON public.leaderboard (player_id);

-- ---------------------------------------------------------------------
-- 2. BUG 2 — Guard "só melhora o tempo"
--    No UPSERT (ON CONFLICT DO UPDATE), se o novo tempo for PIOR ou igual,
--    mantém os valores antigos. Garante que o leaderboard guarda o MELHOR
--    tempo por jogador, não o último.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.manter_melhor_tempo()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.tempo >= OLD.tempo THEN
    NEW.tempo := OLD.tempo;
    NEW.nome := OLD.nome;
    NEW.created_at := OLD.created_at;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_manter_melhor_tempo ON public.leaderboard;
CREATE TRIGGER trigger_manter_melhor_tempo
  BEFORE UPDATE ON public.leaderboard
  FOR EACH ROW EXECUTE FUNCTION public.manter_melhor_tempo();

-- ---------------------------------------------------------------------
-- 3. BUG 3 — Retenção top-10 no servidor
--    Backfill dos legados (player_id NULL) para um UUID determinístico antes
--    de aplicar a limpeza, evitando o furo do NOT IN com NULL.
-- ---------------------------------------------------------------------
UPDATE public.leaderboard
  SET player_id = gen_random_uuid()::text
  WHERE player_id IS NULL;

CREATE OR REPLACE FUNCTION public.limpar_leaderboard()
RETURNS TRIGGER AS $$
BEGIN
  -- Mantém só as 10 melhores (menor tempo); desempate determinístico por
  -- created_at e id. Usa a PK (id) no NOT IN — nunca NULL.
  DELETE FROM public.leaderboard
  WHERE id NOT IN (
    SELECT id FROM public.leaderboard
    ORDER BY tempo ASC, created_at ASC, id ASC
    LIMIT 10
  );
  RETURN NULL;  -- AFTER trigger: valor de retorno ignorado
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_limpar_leaderboard ON public.leaderboard;
CREATE TRIGGER trigger_limpar_leaderboard
  AFTER INSERT OR UPDATE ON public.leaderboard
  FOR EACH ROW EXECUTE FUNCTION public.limpar_leaderboard();

-- ---------------------------------------------------------------------
-- 4. BUG 1 — Remover a coluna `data` manual (RODAR DEPOIS DO DEPLOY)
--    Descomente e rode SÓ depois que todos os clientes estiverem na v1.1.0.
-- ---------------------------------------------------------------------
-- ALTER TABLE public.leaderboard DROP COLUMN IF EXISTS data;

-- ---------------------------------------------------------------------
-- 5. BLOQUEIO conhecido — GRANTs (sem isto o leaderboard fica VAZIO)
--    RLS sozinho não basta; a role anon precisa dos privilégios de tabela.
-- ---------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON public.leaderboard TO anon;
GRANT EXECUTE ON FUNCTION public.limpar_leaderboard() TO anon;
GRANT EXECUTE ON FUNCTION public.manter_melhor_tempo() TO anon;

-- Lembre-se das POLICIES de RLS (se RLS estiver ativo) permitindo SELECT/INSERT/
-- UPDATE para anon — o GRANT é necessário, mas não substitui a policy.
