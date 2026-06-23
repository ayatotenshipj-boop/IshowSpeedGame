# Build — Executável do Speed Vs Labubu

O jogo é empacotado com **PyInstaller** em arquivo único (`--onefile`), com todos
os assets e o `config/` embutidos. Em runtime, `config/settings.py` detecta o
modo empacotado (`sys.frozen`) e lê os dados de `sys._MEIPASS`.

> **Importante:** o PyInstaller **não faz cross-compile**. Um `.exe` de Windows
> só pode ser gerado **no Windows** (ou via Windows-Python rodando sob Wine).
> No Linux, o resultado é um executável Linux (ELF). Para distribuir a
> "qualquer pessoa" no Windows, rode o passo abaixo numa máquina Windows.

## Windows (gera `SpeedVsLabubu.exe`)

Pré-requisito: Python 3.11+ instalado (marque "Add Python to PATH").

```bat
py -m venv .build-venv
.build-venv\Scripts\activate
pip install pyinstaller pygame-ce pygame-gui pillow
pyinstaller SpeedVsLabubu.spec
```

Saída: `dist\SpeedVsLabubu.exe` (arquivo único, ~60 MB). É só enviar esse
`.exe` — não precisa instalar Python no PC de quem for jogar.

Atalho: rode `build_windows.bat` (faz tudo acima).

## Linux (gera executável Linux)

```bash
python -m venv .build-venv
./.build-venv/bin/pip install pyinstaller pygame-ce pygame-gui pillow
./.build-venv/bin/pyinstaller SpeedVsLabubu.spec
# saída: dist/SpeedVsLabubu
```

## O que o `.spec` embute
- `assets/` (sprites, mapa, áudios) e `config/` (settings + path.json)
- dados do `pygame_gui` (temas)
- modo `--windowed` (sem console), arquivo único

## Controles
- Mouse: selecionar carta / posicionar torre / clicar torre (painel).
- ESC: fecha painel → deseleciona carta → pausa.
- F11: alterna tela cheia / janela.
