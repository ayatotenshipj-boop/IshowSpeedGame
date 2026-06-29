-- Migration 002: adicionar suporte a categorias no leaderboard
-- Executar no Supabase SQL Editor (Dashboard → SQL Editor)
-- Idempotente: IF NOT EXISTS garante segurança em re-execuções

ALTER TABLE leaderboard
    ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'normal_speedrun';

ALTER TABLE leaderboard
    ADD COLUMN IF NOT EXISTS valor NUMERIC;

-- índice composto para queries por categoria (performance)
CREATE INDEX IF NOT EXISTS idx_leaderboard_category_valor
    ON leaderboard (category, valor);

-- permissão para role anon (necessária para SELECT/INSERT via PostgREST)
GRANT SELECT, INSERT ON leaderboard TO anon;
