-- Migration: corrige PK do leaderboard de player_id → (player_id, category)
--
-- PROBLEMA: PK era apenas player_id, causando 409 ao registrar o mesmo
-- jogador em categorias diferentes (normal_speedrun, hard_speedrun, infinite_waves).
--
-- SOLUÇÃO: PK composta (player_id, category) — um registro por jogador por modo.
--
-- COMO EXECUTAR: Supabase Dashboard → SQL Editor → colar e rodar.
-- ORDEM IMPORTA: DROP constraint antes de ADD.

-- 1. Remove a PK atual (player_id sozinho).
ALTER TABLE leaderboard DROP CONSTRAINT IF EXISTS leaderboard_pkey;

-- 2. Remove índice único legado em player_id, se existir.
DROP INDEX IF EXISTS leaderboard_player_id_key;

-- 3. Adiciona PK composta: um registro por jogador por categoria.
ALTER TABLE leaderboard ADD PRIMARY KEY (player_id, category);

-- 4. Índice de leitura eficiente por categoria + campo de score.
CREATE INDEX IF NOT EXISTS idx_lb_cat_tempo  ON leaderboard (category, tempo  ASC);
CREATE INDEX IF NOT EXISTS idx_lb_cat_valor  ON leaderboard (category, valor  DESC);

-- 5. Garante que role anon pode ler e inserir (RLS não basta sozinho).
GRANT SELECT, INSERT, UPDATE ON leaderboard TO anon;
