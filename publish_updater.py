import os
import sys
import json
import subprocess
import requests
from pathlib import Path

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
GITHUB_USER = "ayatotenshipj-boop"
GITHUB_REPO = "IshowSpeedGame"
VERSION = "1.3.1" # Alterado para 1.3.1 para não conflitar com a tag anterior
CHANGELOG = """v1.3.1 - Meta Diversificada e Correcoes

[Economia]
- Inimigos agora concedem +5% de ouro por wave progressiva, financiando upgrades no late-game.

[Torres - Buffs]
- Shake It Speed: Dano base aumentado (8 -> 9).
- Suprised Speed: Dano (11 -> 14) e cadencia (1.05 -> 1.15) aumentados.
- SayWallahi Speed: Alcance critico aumentado (90 -> 135) e cadencia (0.42 -> 0.55).
- KindaHomeless Speed: Custo reduzido de 1500 para 175. Efeito de slow melhorado (50% -> 60%).

[Torres - Nerfs]
- ShockedSpeed: Custo aumentado (130 -> 160) e dano base reduzido (19 -> 15) para conter seu dominio.

[Inimigos]
- Labubu4 (Cansado): Agora perde 5% de velocidade em TODAS as curvas, comecando pela primeira.

[Boss]
- Ancelotti: Adicionado Cooldown Interno de 5s apos ser stunnado (fim do perma-stun).
- Ancelotti: Invocacao de Labubu MUI limitada por timer (1 a cada 2.5s) em vez de chance por hit.

[Correcoes]
- Erro 400 Bad Request no Leaderboard (Supabase) corrigido.
- Colunas do banco alinhadas com o codigo Python.
"""

# Arquivos gerados pelo PyInstaller
LINUX_BIN = "dist/SpeedVsLabubu-Linux"
WINDOWS_BIN = "dist/SpeedVsLabubu-Windows.exe"

def run_cmd(cmd):
    """Executa um comando no terminal e imprime a saída."""
    print(f">>> Executando: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.stdout: print(result.stdout)
    if result.stderr: print(result.stderr)
    if result.returncode != 0:
        print("❌ Erro ao executar comando.")
        sys.exit(1)

def main():
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        github_token = input("Cole seu GitHub Personal Access Token (ghp_...): ").strip()
    
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 1. Atualizar version.json
    print("\n[1/5] Atualizando version.json...")
    version_data = {
        "version": VERSION,
        "name": "Speed Vs Labubu Remake",
        "changelog": CHANGELOG,
        "download_url": {
            "linux": f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/v{VERSION}/SpeedVsLabubu-Linux",
            "windows": f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/v{VERSION}/SpeedVsLabubu-Windows.exe"
        },
        "files": []
    }
    with open("version.json", "w", encoding="utf-8") as f:
        json.dump(version_data, f, ensure_ascii=False, indent=2)

    # 2. Compilar com PyInstaller
    print("\n[2/5] Compilando com PyInstaller...")
    run_cmd("pyinstaller --noconfirm --onefile --noconsole main.py")
    
    # Renomear o executável gerado
    if sys.platform == "win32":
        if Path("dist/main.exe").exists():
            os.replace("dist/main.exe", WINDOWS_BIN)
        asset_to_upload = WINDOWS_BIN
    else:
        if Path("dist/main").exists():
            os.replace("dist/main", LINUX_BIN)
        os.chmod(LINUX_BIN, 0o755)
        asset_to_upload = LINUX_BIN

    if not Path(asset_to_upload).exists():
        print(f"❌ Erro: Executável {asset_to_upload} não encontrado após compilação.")
        sys.exit(1)

    # 3. Git Commit e Push (Envia todos os arquivos .py e assets)
    print("\n[3/5] Enviando código para o GitHub (Git Push)...")
    run_cmd("git add .")
    run_cmd(f'git commit -m "Release v{VERSION}: Balanceamento e correcoes"')
    run_cmd("git push origin main")

    # 4. Criar Tag
    print(f"\n[4/5] Criando tag v{VERSION}...")
    run_cmd(f"git tag v{VERSION}")
    run_cmd(f"git push origin v{VERSION}")

    # 5. Criar Release no GitHub e fazer Upload do Executável
    print(f"\n[5/5] Criando Release no GitHub e subindo {asset_to_upload}...")
    
    release_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases"
    release_payload = {
        "tag_name": f"v{VERSION}",
        "name": f"v{VERSION}",
        "body": CHANGELOG,
        "draft": False,
        "prerelease": False
    }
    
    resp = requests.post(release_url, headers=headers, json=release_payload)
    if resp.status_code != 201:
        print(f"❌ Erro ao criar release: {resp.json()}")
        sys.exit(1)
        
    release_data = resp.json()
    upload_url = release_data["upload_url"].replace("{?name,label}", "")
    print(f"✅ Release v{VERSION} criada com sucesso!")

    # Upload do Asset (Executável)
    asset_name = os.path.basename(asset_to_upload)
    with open(asset_to_upload, "rb") as f:
        upload_headers = headers.copy()
        upload_headers["Content-Type"] = "application/octet-stream"
        
        print(f"⏳ Fazendo upload de {asset_name} (isso pode demorar)...")
        resp_upload = requests.post(
            f"{upload_url}?name={asset_name}",
            headers=upload_headers,
            data=f
        )
        
    if resp_upload.status_code == 201:
        print(f"✅ Upload de {asset_name} concluído com sucesso!")
    else:
        print(f"❌ Erro no upload do asset: {resp_upload.json()}")

    print("\n🚀 ATUALIZAÇÃO PUBLICADA COM SUCESSO! 🚀")

if __name__ == "__main__":
    main()