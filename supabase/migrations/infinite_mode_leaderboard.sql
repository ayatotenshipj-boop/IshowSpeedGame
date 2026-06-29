-- Migração: adicionar suporte ao Modo Infinito no leaderboard
-- Idempotente: pode ser executada mais de uma vez sem erro.
-- Rodar no SQL Editor do Supabase Dashboard.
--
-- O modo infinito usa category='infinite_waves' e ordena por valor DESC
-- (maior número de waves completadas = melhor score).

-- 1. Verificar schema atual antes de alterar
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'leaderboard'
ORDER BY ordinal_position;

-- 2. Adicionar coluna category se não existir (retrocompatível)
ALTER TABLE leaderboard
ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'normal_speedrun';

-- 3. Adicionar coluna valor se não existir (score genérico: tempo ou waves)
ALTER TABLE leaderboard
ADD COLUMN IF NOT EXISTS valor NUMERIC;

-- 4. Atualizar registros sem category (legado normal_speedrun)
UPDATE leaderboard
SET category = 'normal_speedrun'
WHERE category IS NULL;

-- 5. Índice para query por categoria ordenada (infinite_waves DESC)
CREATE INDEX IF NOT EXISTS idx_leaderboard_infinito
ON leaderboard(category, valor DESC)
WHERE category = 'infinite_waves';

-- 6. Permissão para a role anon (leitura e inserção)
GRANT SELECT, INSERT ON leaderboard TO anon;

-- 7. Verificação final
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'leaderboard'
  AND column_name IN ('category', 'valor');
