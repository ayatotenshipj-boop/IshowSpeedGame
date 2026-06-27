#!/usr/bin/env python3
"""Publisher interativo — Speed Vs Labubu Remake.

Fluxo:
  1. Lê versão atual do version.json e sugere próximas versões
  2. Coleta changelog interativamente por seções
  3. Atualiza version.json
  4. Faz git commit + push
  5. Compila com PyInstaller (usa .build-venv se disponível)
  6. Cria tag + GitHub Release + upload do executável
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────
GITHUB_USER = "ayatotenshipj-boop"
GITHUB_REPO = "IshowSpeedGame"
RAIZ = Path(__file__).resolve().parent

LINUX_SPEC   = RAIZ / "SpeedVsLabubu-Linux.spec"
LINUX_BIN    = RAIZ / "dist" / "SpeedVsLabubu-Linux"
WINDOWS_BIN  = RAIZ / "dist" / "SpeedVsLabubu-Windows.exe"
BUILD_VENV   = RAIZ / ".build-venv"

# Pyinstaller preferencial: build-venv > sistema.
if sys.platform == "win32":
    _PYINST = BUILD_VENV / "Scripts" / "pyinstaller.exe"
else:
    _PYINST = BUILD_VENV / "bin" / "pyinstaller"
PYINSTALLER = str(_PYINST) if _PYINST.exists() else "pyinstaller"


# ── Helpers ──────────────────────────────────────────────────────────────────

def cor(texto: str, codigo: str) -> str:
    """Aplica cor ANSI se o terminal suportar."""
    if sys.platform == "win32" and not os.environ.get("ANSICON"):
        return texto
    codigos = {"verde": "32", "amarelo": "33", "vermelho": "31",
               "ciano": "36", "bold": "1", "dim": "2"}
    return f"\033[{codigos.get(codigo, '0')}m{texto}\033[0m"


def ok(msg: str) -> None:
    print(cor(f"  ✓ {msg}", "verde"))

def err(msg: str) -> None:
    print(cor(f"  ✗ {msg}", "vermelho"))
    sys.exit(1)

def info(msg: str) -> None:
    print(cor(f"  → {msg}", "ciano"))

def titulo(msg: str) -> None:
    print("\n" + cor(f"══ {msg} ══", "bold"))


def run(cmd: str | list, desc: str = "", check: bool = True) -> subprocess.CompletedProcess:
    """Executa comando e exibe saída; aborta em erro se check=True."""
    if desc:
        info(desc)
    shell = isinstance(cmd, str)
    result = subprocess.run(cmd, shell=shell, text=True, capture_output=True, cwd=RAIZ)
    if result.stdout.strip():
        print(cor(result.stdout.strip(), "dim"))
    if result.returncode != 0:
        if result.stderr.strip():
            print(cor(result.stderr.strip(), "vermelho"))
        if check:
            err(f"Comando falhou (código {result.returncode}): {cmd}")
    return result


def ler_version_json() -> dict:
    caminho = RAIZ / "version.json"
    if not caminho.exists():
        return {"version": "1.0.0"}
    with caminho.open(encoding="utf-8") as f:
        return json.load(f)


def salvar_version_json(dados: dict) -> None:
    with (RAIZ / "version.json").open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    ok("version.json atualizado")


# ── Versão ───────────────────────────────────────────────────────────────────

def _bump(versao: str, parte: int) -> str:
    """Incrementa a parte (0=major, 1=minor, 2=patch) e zera as menores."""
    partes = [int(p) for p in versao.split(".")]
    while len(partes) < 3:
        partes.append(0)
    partes[parte] += 1
    for i in range(parte + 1, 3):
        partes[i] = 0
    return ".".join(str(p) for p in partes)


def perguntar_versao(versao_atual: str) -> str:
    patch  = _bump(versao_atual, 2)
    minor  = _bump(versao_atual, 1)
    major  = _bump(versao_atual, 0)

    print(f"\n  Versão atual: {cor(versao_atual, 'amarelo')}")
    print(f"  [1] {cor(patch,  'verde')}  ← patch  (bug fix / pequena melhoria)")
    print(f"  [2] {cor(minor,  'verde')}  ← minor  (nova feature)")
    print(f"  [3] {cor(major,  'verde')}  ← major  (mudança grande)")
    print(f"  [4] digitar manualmente")

    opcoes = {"1": patch, "2": minor, "3": major}
    while True:
        escolha = input("\n  Qual versão? [1/2/3/4]: ").strip()
        if escolha in opcoes:
            v = opcoes[escolha]
            print(f"  → Versão escolhida: {cor(v, 'verde')}")
            return v
        if escolha == "4":
            while True:
                v = input("  Digite a versão (ex: 1.4.0): ").strip()
                if v and all(c.isdigit() or c == "." for c in v):
                    return v
                print("  Formato inválido. Use X.Y.Z")
        print("  Opção inválida.")


# ── Changelog ────────────────────────────────────────────────────────────────

_SECOES_PADRAO = [
    "Novidades", "Torres - Buffs", "Torres - Nerfs",
    "Inimigos", "Boss", "Economia", "Visual / UI", "Correções",
]


def perguntar_changelog(versao: str) -> str:
    """Coleta o changelog interativamente por seções."""
    print(f"\n  {cor('Changelog para v' + versao, 'bold')}")
    print(f"  {cor('Dica: Enter em branco numa linha encerra a seção. Seção vazia é pulada.', 'dim')}")

    titulo_release = input(f"\n  Título da release (ex: Balanceamento e VFX): ").strip()
    if not titulo_release:
        titulo_release = f"Atualização {versao}"

    secoes: list[tuple[str, list[str]]] = []

    # Seções padrão
    for nome_sec in _SECOES_PADRAO:
        items: list[str] = []
        print(f"\n  {cor('[' + nome_sec + ']', 'ciano')}  (Enter em branco para pular)")
        while True:
            item = input(f"    - ").strip()
            if not item:
                break
            items.append(item)
        if items:
            secoes.append((nome_sec, items))

    # Seção extra avulsa
    while True:
        nova = input(f"\n  Adicionar seção extra? (nome ou Enter para terminar): ").strip()
        if not nova:
            break
        items = []
        while True:
            item = input(f"    [{nova}] - ").strip()
            if not item:
                break
            items.append(item)
        if items:
            secoes.append((nova, items))

    # Monta texto
    linhas = [f"v{versao} - {titulo_release}", ""]
    for nome_sec, items in secoes:
        linhas.append(f"[{nome_sec}]")
        for item in items:
            linhas.append(f"- {item}")
        linhas.append("")

    texto = "\n".join(linhas).strip()

    print(f"\n  {cor('─── Preview do changelog ───', 'dim')}")
    for linha in texto.split("\n"):
        print(f"    {linha}")
    print(f"  {cor('────────────────────────────', 'dim')}")

    confirma = input("\n  Confirmar changelog? [S/n]: ").strip().lower()
    if confirma == "n":
        print("  Encerrando.")
        sys.exit(0)

    return texto


# ── Git ──────────────────────────────────────────────────────────────────────

def git_commit_push(versao: str) -> None:
    titulo("Git: commit + push")

    # Status rápido
    r = run("git status --short", "Verificando alterações...", check=False)
    if not r.stdout.strip():
        print(cor("  Nenhuma alteração staged. Fazendo add de todos os arquivos .py e json.", "amarelo"))

    run("git add .", "git add .")
    run(
        f'git commit -m "release: v{versao}"',
        f"git commit v{versao}",
        check=False,  # pode não ter nada novo
    )
    run("git push origin main", "git push origin main")
    ok("Código enviado para main")


def git_tag(versao: str) -> None:
    titulo("Git: tag")
    # Remove tag local se existir (re-release do mesmo número é comum em dev)
    run(f"git tag -d v{versao}", check=False)
    run(f"git push origin :refs/tags/v{versao}", check=False)
    run(f"git tag v{versao}", f"Criando tag v{versao}")
    run(f"git push origin v{versao}", f"Enviando tag v{versao}")
    ok(f"Tag v{versao} criada e enviada")


# ── Build ────────────────────────────────────────────────────────────────────

def compilar() -> Path:
    titulo("Build — PyInstaller")

    spec = LINUX_SPEC if sys.platform != "win32" else RAIZ / "main.spec"
    if not spec.exists():
        err(f"Arquivo .spec não encontrado: {spec}")

    info(f"Usando spec: {spec.name}")
    info(f"Usando pyinstaller: {PYINSTALLER}")

    run(
        f'"{PYINSTALLER}" --noconfirm "{spec}"',
        "Compilando (pode demorar ~1-2 min)...",
    )

    # Localiza o binário gerado
    if sys.platform == "win32":
        bin_path = WINDOWS_BIN
        nome_exe = bin_path.name
    else:
        bin_path = LINUX_BIN
        nome_exe = bin_path.name
        if bin_path.exists():
            bin_path.chmod(0o755)

    if not bin_path.exists():
        err(f"Executável não encontrado após build: {bin_path}")

    tamanho_mb = bin_path.stat().st_size / (1024 * 1024)
    ok(f"{nome_exe}  ({tamanho_mb:.1f} MB)")
    return bin_path


# ── GitHub Release ────────────────────────────────────────────────────────────

def _github_headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def obter_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print(f"\n  {cor('Token GitHub necessário para criar Release.', 'amarelo')}")
        print("  Dica: export GITHUB_TOKEN=ghp_... antes de rodar o script.")
        token = input("  Cole seu Personal Access Token (ghp_...): ").strip()
    if not token:
        err("Token não fornecido.")
    return token


def criar_release(versao: str, changelog: str, token: str) -> str:
    """Cria a Release no GitHub e retorna o upload_url."""
    import urllib.request as ur
    import urllib.error

    titulo("GitHub Release")
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases"
    payload = json.dumps({
        "tag_name": f"v{versao}",
        "name": f"v{versao}",
        "body": changelog,
        "draft": False,
        "prerelease": False,
    }).encode()

    req = ur.Request(url, data=payload, headers=_github_headers(token), method="POST")
    try:
        with ur.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        corpo = e.read().decode()
        # Se a release já existe, pergunta se quer deletar e recriar.
        if e.code == 422 and "already_exists" in corpo:
            print(cor("  Release já existe para essa tag.", "amarelo"))
            if input("  Deletar e recriar? [s/N]: ").strip().lower() == "s":
                _deletar_release_existente(versao, token)
                return criar_release(versao, changelog, token)
            err("Release já existe. Escolha outra versão ou delete manualmente.")
        err(f"Erro ao criar release ({e.code}): {corpo}")

    upload_url = data["upload_url"].replace("{?name,label}", "")
    ok(f"Release v{versao} criada")
    return upload_url


def _deletar_release_existente(versao: str, token: str) -> None:
    import urllib.request as ur
    # Busca release pela tag
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/tags/v{versao}"
    req = ur.Request(url, headers=_github_headers(token), method="GET")
    try:
        with ur.urlopen(req, timeout=10) as r:
            release_id = json.loads(r.read())["id"]
    except Exception:
        return
    del_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/{release_id}"
    req2 = ur.Request(del_url, headers=_github_headers(token), method="DELETE")
    try:
        ur.urlopen(req2, timeout=10)
        ok("Release anterior deletada")
    except Exception:
        pass


def upload_asset(upload_url: str, bin_path: Path, token: str) -> None:
    import urllib.request as ur

    info(f"Enviando {bin_path.name} ({bin_path.stat().st_size/(1024*1024):.1f} MB)...")
    headers = _github_headers(token)
    headers["Content-Type"] = "application/octet-stream"

    with bin_path.open("rb") as f:
        dados = f.read()

    req = ur.Request(
        f"{upload_url}?name={bin_path.name}",
        data=dados,
        headers=headers,
        method="POST",
    )
    try:
        with ur.urlopen(req, timeout=300) as r:
            if r.status == 201:
                ok(f"Upload concluído: {bin_path.name}")
            else:
                err(f"Upload retornou status {r.status}")
    except Exception as e:
        err(f"Erro no upload: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────

def confirmar(pergunta: str) -> bool:
    return input(f"\n  {pergunta} [S/n]: ").strip().lower() != "n"


def main() -> None:
    print(cor("\n╔══════════════════════════════════════╗", "bold"))
    print(cor("║   Speed Vs Labubu — Publisher v2     ║", "bold"))
    print(cor("╚══════════════════════════════════════╝", "bold"))

    vjson = ler_version_json()
    versao_atual = vjson.get("version", "1.0.0")

    # ── 1. Versão ────────────────────────────────────────────────────────────
    titulo("Versão")
    versao = perguntar_versao(versao_atual)

    # ── 2. Changelog ─────────────────────────────────────────────────────────
    titulo("Changelog")
    changelog = perguntar_changelog(versao)

    # ── 3. Confirma token antes de começar o trabalho pesado ─────────────────
    token = obter_token()

    # ── 4. Atualiza version.json ──────────────────────────────────────────────
    titulo("version.json")
    version_data = {
        "version": versao,
        "name": "Speed Vs Labubu Remake",
        "changelog": changelog,
        "download_url": {
            "linux":   f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/v{versao}/SpeedVsLabubu-Linux",
            "windows": f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/v{versao}/SpeedVsLabubu-Windows.exe",
        },
        "files": [],
    }
    salvar_version_json(version_data)

    # ── 5. Git commit + push ──────────────────────────────────────────────────
    git_commit_push(versao)

    # ── 6. Build ──────────────────────────────────────────────────────────────
    if confirmar("Compilar o executável agora?"):
        bin_path = compilar()
    else:
        # Usa o binário existente em dist/
        bin_path = LINUX_BIN if sys.platform != "win32" else WINDOWS_BIN
        if not bin_path.exists():
            err(f"Nenhum executável em {bin_path}. Execute a compilação.")
        info(f"Usando binário existente: {bin_path.name}")

    # ── 7. Tag ────────────────────────────────────────────────────────────────
    git_tag(versao)

    # ── 8. Release + Upload ───────────────────────────────────────────────────
    upload_url = criar_release(versao, changelog, token)
    upload_asset(upload_url, bin_path, token)

    print(cor(f"\n  🚀  v{versao} publicada com sucesso!", "verde"))
    print(cor(f"  https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/tag/v{versao}\n", "dim"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(cor("\n\n  Cancelado pelo usuário.", "amarelo"))
        sys.exit(0)
