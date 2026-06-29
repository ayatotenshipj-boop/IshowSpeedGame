-- ============================================================
-- Correção: coluna 'valor' e 'category' podem não existir
-- Rodar no SQL Editor do Supabase Dashboard
-- ============================================================

-- 1. Inspecionar schema atual (rodar antes do passo 2 para confirmar)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'leaderboard'
ORDER BY ordinal_position;

-- 2. Garantir coluna 'category' (pode já existir — IF NOT EXISTS é seguro)
ALTER TABLE leaderboard ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'normal_speedrun';

-- 3. Garantir coluna 'valor' (se chamada 'value' no banco, renomear primeiro)
--    Se o passo 1 mostrou 'value', rodar:
--    ALTER TABLE leaderboard RENAME COLUMN value TO valor;
--    Depois rodar o ADD COLUMN abaixo (será no-op se já existe após rename):
ALTER TABLE leaderboard ADD COLUMN IF NOT EXISTS valor NUMERIC;

-- 4. Índice para queries por categoria + valor
CREATE INDEX IF NOT EXISTS idx_leaderboard_category_valor
ON leaderboard (category, valor);

-- 5. Constraint única para o UPSERT por (player_id, category)
--    Necessária para o ON CONFLICT funcionar no registrar_vitoria.
--    Se já existir uma UNIQUE só em player_id, ela não conflita — pode coexistir.
ALTER TABLE leaderboard
    ADD CONSTRAINT leaderboard_player_category_unique
    UNIQUE (player_id, category);

-- 6. Garantir permissões para role anon
GRANT SELECT, INSERT ON leaderboard TO anon;

-- 6. Verificação final — deve retornar 'valor' e 'category'
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'leaderboard'
  AND column_name IN ('valor', 'category', 'value')
ORDER BY column_name;
