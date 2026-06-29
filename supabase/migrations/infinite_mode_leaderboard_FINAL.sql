-- ============================================================
-- Modo Infinito — migration final consolidada
-- Colar inteiro no SQL Editor do Supabase Dashboard e executar
-- Idempotente: pode ser executada mais de uma vez sem erro.
-- ============================================================

-- Passo 1: inspecionar schema atual (apenas leitura)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'leaderboard'
ORDER BY ordinal_position;

-- Passo 2: adicionar colunas (idempotente)
ALTER TABLE leaderboard
ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'normal_speedrun';

ALTER TABLE leaderboard
ADD COLUMN IF NOT EXISTS valor NUMERIC;

-- Passo 3: preencher registros legados sem category
UPDATE leaderboard
SET category = 'normal_speedrun'
WHERE category IS NULL;

-- Passo 4: índice para infinite_waves (ordena DESC — mais waves = melhor)
CREATE INDEX IF NOT EXISTS idx_leaderboard_infinito
ON leaderboard(category, valor DESC)
WHERE category = 'infinite_waves';

-- Passo 5: índice para speedrun (ordena ASC — menor tempo = melhor)
CREATE INDEX IF NOT EXISTS idx_leaderboard_speedrun
ON leaderboard(category, valor ASC)
WHERE category IN ('normal_speedrun', 'hard_speedrun');

-- Passo 6: permissão para a role anon (leitura e inserção)
GRANT SELECT, INSERT ON leaderboard TO anon;

-- Passo 7: verificação final — deve retornar as duas colunas
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'leaderboard'
  AND column_name IN ('category', 'valor');

-- Passo 8 (opcional, remover após confirmar): teste de insert e limpeza
-- INSERT INTO leaderboard (jogador, category, valor)
-- VALUES ('teste_infinito', 'infinite_waves', 5);
-- SELECT * FROM leaderboard WHERE category = 'infinite_waves';
-- DELETE FROM leaderboard WHERE jogador = 'teste_infinito';
