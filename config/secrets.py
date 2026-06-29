# config/secrets.py
# Credenciais externas. Variáveis de ambiente têm prioridade; fallback usa a
# chave anon pública do Supabase (projetada para ser embarcada em clientes —
# veja https://supabase.com/docs/guides/api#api-keys). Para sobrescrever localmente,
# copie .env.example → .env e preencha os valores.

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

_DEFAULT_URL = "https://kooausbgcmhmijgqjcpd.supabase.co"
_DEFAULT_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtvb2F1c2JnY21obWlqZ3FqY3BkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIyNDYxNDYsImV4cCI6MjA5NzgyMjE0Nn0"
    ".k_7Dd06RqzqCXicuZ-Ft0vMmvW-V6M_YFYuIYs19uss"
)

SUPABASE_URL: str = os.getenv("SUPABASE_URL", _DEFAULT_URL)
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", _DEFAULT_KEY)
