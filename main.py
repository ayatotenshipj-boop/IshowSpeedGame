"""Entrypoint do jogo Speed Vs Labubu.

Inicializa o pygame, abre a janela e roda o game loop principal a 60 FPS em
torno de um StateManager (Menu → Jogo → Pausa → Game Over / Vitória). A flag
`--dev` ativa o modo desenvolvimento (grid, alcances, posições e FPS no título).

Uso:
    python main.py          # modo normal
    python main.py --dev    # modo dev
"""

import logging
import random
import sys
import threading
import time

import pygame
import pygame_gui

from config.settings import (
    FPS,
    HIT_RADIUS,
    HUD_RECT,
    MAP_RECT,
    MODOS_DIFICULDADE,
    RAIZ_PROJETO,
    RENDER_HEIGHT,
    RENDER_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    COR_FUNDO_TELA,
    COR_CIANO,
    COR_OVERLAY_LIVRE,
    COR_OVERLAY_PATH,
    COR_OVERLAY_VALIDO,
    COR_OVERLAY_INVALIDO,
    ALPHA_OVERLAY_GLOBAL,
    ALPHA_OVERLAY_HOVER,
    COR_MAP_GRAYSCALE,
)
from core.asset_manager import AssetManager
from core.audio import AudioManager
from core.game_state import GameState
from core.state_manager import GameScreen, StateManager
from core.updater import Updater
from core import conquistas, leaderboard
from entities.boss import Ancelotti
from entities.tower import SPRITE_SIZE, TOWER_TYPES, Speed5, Speed7
from entities.wave_manager import WAVES
from map.game_map import GameMap
from map.placement_grid import PlacementGrid
from ui.card_hand import CardHand
from ui.changelog_screen import (
    ChangelogScreen,
    changelog_ja_visto,
    ler_version_json,
    marcar_changelog_visto,
)
from ui.diff_selector import DiffSelectorWidget
from ui.hud import HUD
from ui.intro_scene import IntroScene
from ui.leaderboard_screen import LeaderboardScreen
from ui.menus import GameOverScreen, MenuScreen, PauseScreen, VictoryScreen
from ui.modo_screen import ModoScreen
from ui.nome_vitoria_screen import NomeVitoriaScreen
from ui.tower_panel import TowerPanel
from ui.update_screen import (
    UpdateCheckScreen,
    UpdateProgressScreen,
    UpdateResultScreen,
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def modo_dev_ativo() -> bool:
    """Indica se a flag `--dev` foi passada na linha de comando."""
    return "--dev" in sys.argv


# --- Escala adaptativa / letterbox --------------------------------------- #
# Tudo é desenhado numa Surface interna RENDER_WIDTH×RENDER_HEIGHT e escalado
# para a janela real. Estes globais (atualizados a cada frame) mapeiam
# coordenadas reais → espaço de render para a entrada de mouse.
_scale: float = 1.0
_offset: tuple[int, int] = (0, 0)


def _atualizar_escala(tela: pygame.Surface) -> None:
    """Recalcula fator de escala e deslocamento de letterbox para a janela atual."""
    global _scale, _offset
    win_w, win_h = tela.get_size()
    # Clamp evita divisão por ~0 em janela degenerada (minimizada/0px).
    _scale = max(min(win_w / RENDER_WIDTH, win_h / RENDER_HEIGHT), 1e-6)
    sw, sh = round(RENDER_WIDTH * _scale), round(RENDER_HEIGHT * _scale)
    _offset = ((win_w - sw) // 2, (win_h - sh) // 2)


def to_render(pos: tuple[int, int]) -> tuple[int, int]:
    """Converte uma coordenada real da janela para o espaço de render (1280×720)."""
    return (
        int(round((pos[0] - _offset[0]) / _scale)),
        int(round((pos[1] - _offset[1]) / _scale)),
    )


def _traduzir_evento(evento: pygame.event.Event) -> pygame.event.Event:
    """Reescreve `pos` de eventos de mouse para o espaço de render (preserva o resto)."""
    if evento.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        return pygame.event.Event(evento.type, {**evento.dict, "pos": to_render(evento.pos)})
    return evento


def _apresentar(tela: pygame.Surface, render_surface: pygame.Surface) -> None:
    """Escala a Surface de render para a janela (letterbox) e atualiza a tela."""
    sw, sh = round(RENDER_WIDTH * _scale), round(RENDER_HEIGHT * _scale)
    tela.fill((0, 0, 0))
    tela.blit(pygame.transform.smoothscale(render_surface, (sw, sh)), _offset)
    pygame.display.flip()


def _mostrar_resultado_update(result_screen, tela, render_surface, clock) -> None:
    """Mini-loop que exibe uma UpdateResultScreen até o jogador fechá-la."""
    aguardando = True
    while aguardando:
        clock.tick(FPS)
        _atualizar_escala(tela)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if result_screen.handle_event(_traduzir_evento(evento)):
                aguardando = False
        render_surface.fill(COR_FUNDO_TELA)
        result_screen.draw(render_surface)
        _apresentar(tela, render_surface)


def _executar_fluxo_update(
    updater: Updater,
    tela: pygame.Surface,
    render_surface: pygame.Surface,
    clock: pygame.time.Clock,
) -> None:
    """Fluxo completo de auto-update: verificar → baixar → reiniciar.

    Roda mini-loops próprios desenhando na render_surface (com letterbox).
    Bloqueia o loop principal de propósito: o jogador está parado no menu e a
    verificação de rede roda numa thread para não travar a animação.
    """
    # 1) Verificação de versão em thread (a rede não pode travar o desenho).
    resultado: dict = {"data": None, "done": False}

    def _verificar() -> None:
        resultado["data"] = updater.check_update()
        resultado["done"] = True

    threading.Thread(target=_verificar, daemon=True).start()

    check_screen = UpdateCheckScreen()
    while not resultado["done"]:
        clock.tick(FPS)
        _atualizar_escala(tela)
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        render_surface.fill(COR_FUNDO_TELA)
        check_screen.draw(render_surface)
        _apresentar(tela, render_surface)

    remote = resultado["data"]

    if not updater.is_configured():
        _mostrar_resultado_update(
            UpdateResultScreen(None, "not_configured"), tela, render_surface, clock
        )
        return

    if remote is None:
        # Sem atualização (ou erro de rede tratado como "já atualizado").
        _mostrar_resultado_update(
            UpdateResultScreen(None, "current"), tela, render_surface, clock
        )
        return

    # 2) Há atualização: baixar o EXECUTÁVEL novo da Release (única forma de
    # atualizar código num exe --onefile). Barra de progresso em MB.
    progress_screen = UpdateProgressScreen(remote.get("version"))

    def _progresso_bytes(baixados: int, total: int) -> None:
        _atualizar_escala(tela)
        render_surface.fill(COR_FUNDO_TELA)
        progress_screen.draw(render_surface, baixados, total)
        _apresentar(tela, render_surface)
        pygame.event.pump()  # mantém a janela responsiva durante o download

    url = updater.url_executavel(remote)
    if url is None:
        # Manifesto sem download_url p/ esta plataforma: nada a aplicar.
        _mostrar_resultado_update(
            UpdateResultScreen(None, "error"), tela, render_surface, clock
        )
        return

    tmp_path = updater.download_executable(url, _progresso_bytes)

    if tmp_path is not None:
        updater.save_local_version(remote)
        # Tela "concluído" breve antes de trocar o binário e reiniciar.
        _atualizar_escala(tela)
        render_surface.fill(COR_FUNDO_TELA)
        UpdateResultScreen(
            None, "updated",
            version=remote.get("version"),
            changelog=updater.get_changelog(remote),
        ).draw(render_surface)
        _apresentar(tela, render_surface)
        pygame.time.wait(2000)
        updater.apply_and_restart(tmp_path)  # substitui o exe e reinicia
    else:
        _mostrar_resultado_update(
            UpdateResultScreen(None, "error"), tela, render_surface, clock
        )


def main() -> None:
    """Inicializa o jogo e executa o game loop principal."""
    dev = modo_dev_ativo()

    pygame.init()
    tela = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()
    fullscreen = False

    # Surface interna onde TUDO é desenhado (resolução fixa); depois escalada
    # para a janela real com letterbox. F11 alterna janela/fullscreen.
    render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))
    _atualizar_escala(tela)

    # Carrega todos os assets uma única vez, após o display estar pronto.
    assets = AssetManager()
    assets.carregar_tudo()
    # Aviso PT-BR para assets esperados ausentes (não quebra o jogo).
    assets.verificar_assets_esperados()

    # Recursos persistentes (não dependem da partida).
    game_map = GameMap(assets)
    card_hand = CardHand(assets)
    hud = HUD()
    tower_panel = TowerPanel()
    fonte_dev = pygame.font.SysFont(None, 16)

    # Estado da partida e grid (recriados a cada nova partida).
    grid = PlacementGrid()
    state = GameState()
    state.wave_manager.assets = assets

    # Surfaces de overlay cacheadas — criadas uma vez, reutilizadas por frame.
    overlay_free_surf = pygame.Surface(MAP_RECT.size, pygame.SRCALPHA)
    overlay_free_surf.fill((*COR_OVERLAY_LIVRE, ALPHA_OVERLAY_GLOBAL))
    cinza_surf = pygame.Surface(MAP_RECT.size, pygame.SRCALPHA)
    cinza_surf.fill(COR_MAP_GRAYSCALE)
    preview_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)

    # Waypoints já recalculados pelo recorte do mapa (fonte única no grid).
    # Idênticos a cada recriação do grid, então capturados uma vez aqui.
    waypoints = grid.waypoints

    # Áudio (subsistema persistente: sobrevive a reinícios de partida).
    audio = AudioManager()

    # Imagem de vitória (opcional): ausente -> None, e a tela usa placeholder.
    try:
        victory_image = assets.get("dialogs/victory_image")
    except KeyError:
        victory_image = None

    # Telas e máquina de estados. O jogo começa no MENU; a intro só aparece
    # depois que o jogador clica em JOGAR (MENU -> INTRO -> PLAYING).
    ui_manager = pygame_gui.UIManager(
        (RENDER_WIDTH, RENDER_HEIGHT),
        theme_path=str(RAIZ_PROJETO / "assets" / "ui_theme.json"),
    )
    state_manager = StateManager()
    current_screen = MenuScreen(ui_manager, assets, audio)
    updater = Updater()  # auto-update via GitHub raw (botão "Atualizar" no menu)
    leaderboard_screen: LeaderboardScreen | None = None  # overlay do top 10 no menu
    changelog_screen: ChangelogScreen | None = None  # overlay de novidades no menu
    diff_selector: DiffSelectorWidget | None = None   # seletor in-game de dificuldade
    # Versão e changelog lidos do version.json local (para exibição automática
    # uma vez após atualização e reabertura manual pelo botão [LOG]).
    _vjson = ler_version_json()
    versao_atual = str(_vjson.get("version", ""))
    changelog_texto = str(_vjson.get("changelog", ""))
    # Música de fundo inicia uma vez no boot e segue tocando por menu/intro/jogo
    # (não reinicia ao começar a partida — evita a música "tocar de novo").
    audio.iniciar_fundo()

    def reset_game(modo: str = "normal") -> None:
        """Reinicia o estado da partida (GameState/grid/cartas) no `modo` dado.

        NÃO mexe na música: ela já está tocando desde o menu e deve continuar
        contínua até a partida (evita reinício ao clicar em JOGAR). A restauração
        da música é feita só nas transições de tela (menu/fim de jogo).

        O modo de dificuldade (Bloco 5) define as vidas iniciais e os
        multiplicadores aplicados pelo WaveManager na criação dos inimigos.
        """
        nonlocal state, grid
        state = GameState()
        state.modo_dificuldade = modo
        state.lives = MODOS_DIFICULDADE[modo]["lives"]
        state.wave_manager.assets = assets
        state.wave_manager.modo = modo
        # Waves congeladas até o seletor de dificuldade confirmar o modo.
        state.waves_congeladas = True
        grid = PlacementGrid()
        card_hand.deselect()

    def _talvez_abrir_changelog() -> None:
        """Abre o changelog automaticamente UMA vez por versão, sobre o menu."""
        nonlocal changelog_screen
        if (
            changelog_screen is None
            and isinstance(current_screen, MenuScreen)
            and changelog_texto
            and not changelog_ja_visto(versao_atual)
        ):
            changelog_screen = ChangelogScreen(ui_manager, versao_atual, changelog_texto)
            current_screen.set_botoes_visiveis(False)

    # Exibição automática na primeira abertura após uma atualização.
    _talvez_abrir_changelog()

    if dev:
        logger.info("Modo desenvolvimento ativo.")

    rodando = True
    while rodando:
        dt = clock.tick(FPS) / 1000.0  # segundos desde o último frame
        ui_manager.update(dt)
        _atualizar_escala(tela)  # escala/letterbox da janela atual

        # --- Eventos ---
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
                continue

            # F11: alterna janela 1280×720 <-> fullscreen no tamanho do desktop.
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F11:
                fullscreen = not fullscreen
                if fullscreen:
                    desktop = pygame.display.get_desktop_sizes()[0]
                    tela = pygame.display.set_mode(desktop, pygame.FULLSCREEN)
                else:
                    tela = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                _atualizar_escala(tela)
                continue

            # Eventos de mouse: traduz `pos` para o espaço de render (1280×720)
            # antes de alimentar tanto o pygame_gui quanto os handlers do jogo.
            evento = _traduzir_evento(evento)
            ui_manager.process_events(evento)

            if state_manager.current == GameScreen.INTRO:
                # A intro inicia o fade-out internamente; a transição ocorre no
                # update quando `complete` fica True (não no retorno do evento).
                current_screen.handle_event(evento)

            elif state_manager.current == GameScreen.MENU:
                # Overlay de changelog aberto tem prioridade: só trata ENTENDIDO.
                if changelog_screen is not None:
                    if changelog_screen.handle_event(evento):
                        marcar_changelog_visto(versao_atual)
                        changelog_screen.destroy()
                        changelog_screen = None
                        current_screen.set_botoes_visiveis(True)
                    continue
                # Overlay de leaderboard aberto tem prioridade: só trata FECHAR.
                if leaderboard_screen is not None:
                    if leaderboard_screen.handle_event(evento):
                        leaderboard_screen.destroy()
                        leaderboard_screen = None
                        current_screen.set_botoes_visiveis(True)
                    continue
                acao = current_screen.handle_event(evento)
                if acao == "play":
                    # JOGAR: inicia direto com Normal; seletor in-game aparece em campo.
                    current_screen.destroy()
                    reset_game("normal")
                    current_screen = IntroScene(assets)
                    state_manager.transition(GameScreen.INTRO)
                elif acao == "quit":
                    rodando = False
                elif acao == "update":
                    # Verifica/baixa atualização (mini-loops próprios). Ao voltar,
                    # o loop principal continua desenhando o menu normalmente.
                    _executar_fluxo_update(updater, tela, render_surface, clock)
                elif acao == "leaderboard":
                    # Abre o top 10 sobre o menu; esconde os botões por baixo.
                    leaderboard_screen = LeaderboardScreen(ui_manager)
                    current_screen.set_botoes_visiveis(False)
                elif acao == "changelog":
                    # Abertura manual pelo botão [LOG] (mesmo se já visto).
                    changelog_screen = ChangelogScreen(
                        ui_manager, versao_atual, changelog_texto
                    )
                    current_screen.set_botoes_visiveis(False)

            elif state_manager.current == GameScreen.SELECAO_MODO:
                acao = current_screen.handle_event(evento)
                if acao == "voltar":
                    # Volta ao menu principal sem iniciar partida.
                    current_screen.destroy()
                    current_screen = MenuScreen(ui_manager, assets, audio)
                    state_manager.transition(GameScreen.MENU)
                elif acao in MODOS_DIFICULDADE:
                    # Modo escolhido: prepara a partida e exibe a intro.
                    current_screen.destroy()
                    reset_game(acao)
                    current_screen = IntroScene(assets)
                    state_manager.transition(GameScreen.INTRO)

            elif state_manager.current == GameScreen.PLAYING:
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    # ESC: fecha painel, senão deseleciona carta, senão pausa.
                    if state.selected_tower is not None:
                        state.selected_tower = None
                    elif state.selected_card is not None:
                        card_hand.deselect()
                        state.selected_card = None
                    else:
                        state_manager.transition(GameScreen.PAUSED)
                        current_screen = PauseScreen(ui_manager)
                elif evento.type == pygame.MOUSEBUTTONDOWN:
                    # Seleção de carta / posicionamento de torre.
                    if evento.button == 3:
                        card_hand.deselect()
                        state.selected_card = None
                    elif evento.button == 1:
                        pos = evento.pos
                        # 0a) Seletor de dificuldade in-game tem prioridade máxima.
                        if diff_selector is not None and diff_selector.visible:
                            modo_clicado = diff_selector.handle_click(pos)
                            if modo_clicado:
                                state.modo_dificuldade = modo_clicado
                                state.lives = MODOS_DIFICULDADE[modo_clicado]["lives"]
                                state.wave_manager.modo = modo_clicado
                                state.waves_congeladas = False
                                diff_selector = None
                                continue
                        # 0b) Botões do HUD (velocidade 2× e pular onda) têm
                        # prioridade máxima — evitam posicionar torre por baixo.
                        if hud.speed_button_rect().collidepoint(pos):
                            state.speed_multiplier = (
                                1.0 if state.speed_multiplier >= 2.0 else 2.0
                            )
                            continue
                        # Auto-Skip: toggle sempre disponível durante o jogo.
                        if hud.auto_button_rect().collidepoint(pos):
                            state.auto_skip = not state.auto_skip
                            continue
                        # Skip durante a wave: só quando disponível (15–20s após
                        # o início) — elimina os restantes e dá o bônus.
                        if (
                            state.skip_disponivel
                            and hud.skip_button_rect().collidepoint(pos)
                        ):
                            _executar_skip(state)
                            continue
                        # 1) Painel de torre aberto tem prioridade sobre o resto.
                        acao_painel = (
                            tower_panel.handle_click(pos, state.selected_tower)
                            if state.selected_tower is not None
                            else None
                        )
                        if acao_painel is not None:
                            if acao_painel:
                                _processar_acao_painel(
                                    acao_painel, state, grid, assets, audio
                                )
                            # acao_painel == "" apenas consome o clique.
                        elif HUD_RECT.collidepoint(pos):
                            idx = card_hand.handle_click(pos)
                            if idx is not None:
                                state.selected_tower = None  # selecionar carta fecha painel
                                if idx == state.selected_card:
                                    # Toggle: clicar na carta já selecionada deseleciona.
                                    card_hand.deselect()
                                    state.selected_card = None
                                elif state.coins >= TOWER_TYPES[idx].cost:
                                    card_hand.select(idx)
                                    state.selected_card = idx
                            # Clique no HUD fora de qualquer carta: não faz nada.
                        elif MAP_RECT.collidepoint(pos) and state.selected_card is None:
                            # Sem carta: clique na hitbox circular da torre abre painel.
                            # Usa distância euclidiana (não célula) para evitar seleção errada
                            # quando duas torres estão próximas na mesma área de célula.
                            px, py = pos
                            candidatas = [
                                t for t in state.towers
                                if (px - t.x) ** 2 + (py - t.y) ** 2 <= HIT_RADIUS ** 2
                            ]
                            state.selected_tower = (
                                min(candidatas,
                                    key=lambda t: (px - t.x) ** 2 + (py - t.y) ** 2)
                                if candidatas else None
                            )
                        elif MAP_RECT.collidepoint(pos) and state.selected_card is not None:
                            idx = state.selected_card
                            tipo = TOWER_TYPES[idx]
                            # Posicionamento livre: a torre fica no pixel EXATO do
                            # clique. Nenhum snap ao grid; a célula só serve para
                            # validar o path (is_placeable) e a venda futura.
                            click_x, click_y = pos
                            cx, cy = grid.pixel_to_cell(click_x, click_y)
                            n_tipo = sum(1 for t in state.towers if type(t) is tipo)
                            # Sobreposição rejeitada por distância euclidiana entre
                            # centros (< 2*HIT_RADIUS), sem usar células OCCUPIED.
                            sem_sobreposicao = all(
                                (click_x - t.x) ** 2 + (click_y - t.y) ** 2
                                > (2 * HIT_RADIUS) ** 2
                                for t in state.towers
                            )
                            if (
                                grid.is_placeable(click_x, click_y)
                                and sem_sobreposicao
                                and state.coins >= tipo.cost
                                and n_tipo < tipo.max_no_campo
                            ):
                                state.towers.append(
                                    tipo(assets, click_x, click_y, cx, cy)
                                )
                                state.coins -= tipo.cost
                                card_hand.deselect()
                                state.selected_card = None
                                # Flash verde de confirmação no ponto do clique.
                                state.death_flashes.append(
                                    {"x": click_x, "y": click_y, "timer": 0.3,
                                     "color": (50, 220, 50)}
                                )
                            else:
                                # Flash vermelho de posicionamento inválido.
                                state.death_flashes.append(
                                    {"x": click_x, "y": click_y, "timer": 0.3,
                                     "color": (230, 40, 40)}
                                )

            elif state_manager.current == GameScreen.PAUSED:
                acao = current_screen.handle_event(evento)
                if acao == "resume":
                    current_screen.destroy()
                    current_screen = None
                    state_manager.transition(GameScreen.PLAYING)
                elif acao == "menu":
                    current_screen.destroy()
                    audio.parar()
                    audio.iniciar_fundo()  # restaura música de fundo no menu
                    current_screen = MenuScreen(ui_manager, assets, audio)
                    state_manager.transition(GameScreen.MENU)
                    _talvez_abrir_changelog()

            elif state_manager.current == GameScreen.NOME_VITORIA:
                resultado = current_screen.handle_event(evento)
                if resultado is not None:
                    current_screen.destroy()
                    if resultado:  # nome digitado: registra a vitória em thread
                        threading.Thread(
                            target=lambda nome=resultado: leaderboard.registrar_vitoria(
                                nome, state.tempo_vitoria
                            ),
                            daemon=True,
                        ).start()
                    state_manager.transition(GameScreen.VICTORY)
                    # Conquista por modo: desbloqueia e mostra banner se for nova.
                    conq_id = f"vitoria_{state.modo_dificuldade}"
                    nova = conquistas.desbloquear(conq_id)
                    current_screen = VictoryScreen(
                        ui_manager, state.kills, state.coins, victory_image,
                        tempo=state.tempo_vitoria,
                        nova_conquista=(
                            conquistas.CONQUISTAS_DEF.get(conq_id) if nova else None
                        ),
                    )

            elif state_manager.current in (GameScreen.GAME_OVER, GameScreen.VICTORY):
                acao = current_screen.handle_event(evento)
                if acao == "retry":
                    current_screen.destroy()
                    current_screen = None
                    reset_game(state.modo_dificuldade)  # mantém o modo da partida
                    state_manager.transition(GameScreen.PLAYING)
                elif acao == "menu":
                    current_screen.destroy()
                    audio.parar()
                    audio.iniciar_fundo()  # restaura música de fundo no menu
                    current_screen = MenuScreen(ui_manager, assets, audio)
                    state_manager.transition(GameScreen.MENU)
                    _talvez_abrir_changelog()

        # --- Update ---
        # Velocidade do jogo (2×): afeta lógica e timers de áudio durante o jogo.
        em_jogo = state_manager.current == GameScreen.PLAYING
        dt_efetivo = dt * state.speed_multiplier if em_jogo else dt

        # Áudio avança em tempo real (dt real, NÃO dt_efetivo): os cues tocam em
        # tempo de relógio — o corte de 1s do killthatboy e o crossfade de 3s
        # (mixer.music.fadeout usa ms reais) ficariam dessincronizados sob 2×.
        audio.update(dt)

        # Typewriter + fade-out da cena de introdução (tempo real, sem 2×).
        # Ao terminar, vai direto para a partida (a música segue tocando).
        if state_manager.current == GameScreen.INTRO:
            current_screen.update(dt)
            if current_screen.complete:
                current_screen.destroy()
                current_screen = None
                state_manager.transition(GameScreen.PLAYING)
                # Seletor in-game de dificuldade: 10s no canto superior.
                diff_selector = DiffSelectorWidget()

        if state_manager.current == GameScreen.PLAYING:
            _atualizar_jogo(dt_efetivo, state, waypoints, assets)
            _atualizar_skip(dt_efetivo, state)  # Skip/Auto-Skip durante a wave
            card_hand.update(dt, to_render(pygame.mouse.get_pos()))  # hover (real)

            # Seletor de dificuldade in-game: ticker e aplicação ao timeout.
            if diff_selector is not None:
                modo_confirmado = diff_selector.update(dt)
                if modo_confirmado:
                    state.modo_dificuldade = modo_confirmado
                    state.lives = MODOS_DIFICULDADE[modo_confirmado]["lives"]
                    state.wave_manager.modo = modo_confirmado
                    state.waves_congeladas = False
                    diff_selector = None

            # Cronômetro: inicia no primeiro inimigo que entra em campo (onda 1).
            if state.tempo_inicio == 0.0 and state.enemies:
                state.tempo_inicio = time.time()

            # Efeito do Speed7: usa dt REAL (áudio toca em tempo de relógio, não
            # afetado pelo 2×). Ao zerar, reverte sprites/mapa e retoma a música.
            if state.speed7_effect_timer > 0.0:
                state.speed7_effect_timer -= dt
                if state.speed7_effect_timer <= 0.0:
                    state.speed7_effect_timer = 0.0
                    _encerrar_efeito_speed7(state, assets, audio)

            # Checa derrota.
            if state.lives <= 0:
                # Restaura música de fundo (corta o loop de suspense do Speed7).
                audio.parar()
                audio.iniciar_fundo()
                state_manager.transition(GameScreen.GAME_OVER)
                tempo_sobrev = (time.time() - state.tempo_inicio) if state.tempo_inicio > 0.0 else 0.0
                current_screen = GameOverScreen(
                    ui_manager,
                    kills=state.kills,
                    coins=state.coins,
                    lives=0,
                    onda_atual=state.wave,
                    onda_total=len(WAVES),
                    tempo=tempo_sobrev,
                    modo=state.modo_dificuldade.upper(),
                )
            # Checa vitória (ondas concluídas, sem inimigos e boss derrotado).
            elif (
                state.wave_manager.is_finished()
                and not state.enemies
                and state.boss_defeated
            ):
                # Restaura música de fundo (corta o loop de suspense do Speed7).
                audio.parar()
                audio.iniciar_fundo()
                # Calcula o tempo total e pede o nome para o leaderboard.
                if state.tempo_inicio > 0.0:
                    state.tempo_vitoria = time.time() - state.tempo_inicio
                state_manager.transition(GameScreen.NOME_VITORIA)
                # Busca record anterior para informar o jogador se não bateu.
                _record_atual = leaderboard.buscar_record_proprio()
                current_screen = NomeVitoriaScreen(
                    ui_manager, state.tempo_vitoria, record_anterior=_record_atual
                )

        # Cursor conforme o contexto (apenas em jogo).
        _atualizar_cursor(state_manager, state, card_hand)

        # --- Render --- (tudo desenhado na Surface interna render_surface)
        render_surface.fill(COR_FUNDO_TELA)

        if state_manager.current in (GameScreen.PLAYING, GameScreen.PAUSED):
            _desenhar_mundo(
                render_surface, game_map, state,
                fonte_dev, dev and state_manager.current == GameScreen.PLAYING, grid,
            )
            # Tom acinzentado sobre o mapa após a habilidade do Speed7.
            if state.map_grayscale:
                render_surface.blit(cinza_surf, MAP_RECT.topleft)
            # Overlays de posicionamento (somente em jogo, com carta selecionada):
            # verde onde pode posicionar; trilha vermelha forte onde não pode.
            if (
                state_manager.current == GameScreen.PLAYING
                and state.selected_card is not None
            ):
                render_surface.blit(overlay_free_surf, MAP_RECT.topleft)
                grid.draw_path(
                    render_surface,
                    pygame.time.get_ticks() / 1000.0,
                    color=COR_OVERLAY_PATH,
                    alpha=140,
                )
                # Hitboxes circulares das torres existentes (dourado) + hitbox do cursor.
                _desenhar_hitboxes_torres(render_surface, state.towers)
                # Preview de range (verde=válido, vermelho=inválido) sob o cursor.
                _desenhar_preview(render_surface, state, grid, preview_surf)
            # Painel da torre selecionada (status, upgrade, venda).
            if (
                state_manager.current == GameScreen.PLAYING
                and state.selected_tower is not None
            ):
                state.selected_tower.draw_range(render_surface)
                tower_panel.draw(render_surface, state.selected_tower, state.coins)
            card_hand.draw(render_surface, state.coins, state.towers)
            hud.draw(
                render_surface,
                state.coins,
                state.lives,
                state.wave,
                state.wave_manager.time_to_next_wave(),
                total_waves=len(WAVES),
                boss_wave=(state.wave == len(WAVES)),
                kills=state.kills,
                speed_multiplier=state.speed_multiplier,
                tempo_decorrido=(
                    time.time() - state.tempo_inicio if state.tempo_inicio > 0 else None
                ),
                skip_disponivel=state.skip_disponivel,
                skip_bonus=_skip_bonus(state),
                auto_skip=state.auto_skip,
            )
            # Seletor de dificuldade in-game (se visível).
            if (
                state_manager.current == GameScreen.PLAYING
                and diff_selector is not None
            ):
                diff_selector.draw(render_surface)

            # Tooltip da carta sob o cursor (apenas em jogo, por cima de tudo).
            if state_manager.current == GameScreen.PLAYING:
                card_hand.draw_tooltip(render_surface)

        if current_screen is not None:
            current_screen.draw(render_surface)

        # Overlays do menu (sobre o menu), antes da UI do pygame_gui.
        if leaderboard_screen is not None:
            leaderboard_screen.draw(render_surface)
        if changelog_screen is not None:
            changelog_screen.draw(render_surface)

        ui_manager.draw_ui(render_surface)

        # Escala a Surface interna para a janela real (letterbox) e apresenta.
        _apresentar(tela, render_surface)

        if dev:
            pygame.display.set_caption(
                f"{WINDOW_TITLE} | FPS: {clock.get_fps():.0f}"
            )

    # Restaura o cursor padrão ao sair.
    _definir_cursor(pygame.SYSTEM_CURSOR_ARROW)
    pygame.quit()


def _processar_acao_painel(acao: str, state: GameState, grid, assets, audio) -> None:
    """Executa a ação escolhida no painel da torre selecionada."""
    torre = state.selected_tower
    if torre is None:
        return

    if acao == "upgrade":
        if torre.can_upgrade():
            custo = torre.upgrade_cost()
            if state.coins >= custo:
                state.coins -= custo
                torre.apply_upgrade(custo)
    elif acao == "buff":
        if isinstance(torre, Speed5):
            torre.activate_buff()
    elif acao == "ability":
        if isinstance(torre, Speed7) and torre.use_ability():
            _ativar_habilidade_speed7(state, assets, audio)
    elif acao == "sell":
        # Speed7 NÃO pode ser vendida: vender+reimplantar geraria nova instância
        # com ability_used=False, burlando o uso-único da habilidade global.
        if isinstance(torre, Speed7):
            return
        state.coins += torre.sell_refund()
        if torre in state.towers:
            state.towers.remove(torre)
        grid.set_free_radius(torre.cell_x, torre.cell_y, type(torre).cell_radius)
        state.selected_tower = None
    elif acao == "close":
        state.selected_tower = None


def _ativar_habilidade_speed7(state: GameState, assets, audio) -> None:
    """Habilidade global do Speed7: hitkill de todos os inimigos + efeitos.

    - Toca `killthatboy.mp3` SOBREPOSTO (canal próprio, cortado em 1s).
    - Pausa a música de fundo e toca o suspense UMA vez; ao terminar, a música
      retoma de onde parou (ver `_encerrar_efeito_speed7`).
    - Elimina todos os inimigos em campo (recompensa, kills e flash roxo).
    - Troca o sprite de todas as torres por `speed8` (56×56) e acinzenta o mapa
      enquanto o suspense toca; tudo volta ao normal quando o timer zera.
    """
    audio.ativar_killthatboy()
    # Suspense uma vez; o timer define quanto dura o efeito visual (= duração do
    # áudio, com fallback se o mixer estiver indisponível).
    duracao = audio.tocar_suspense_once()
    state.speed7_effect_timer = duracao if duracao > 0 else 6.0

    for inimigo in state.enemies:
        state.coins += inimigo.reward
        state.kills += 1
        # Se o boss estava em campo, o hitkill também o derrota: marca a flag
        # senão a condição de vitória nunca dispara (partida não acaba).
        if inimigo.name == "Ancelotti":
            state.boss_defeated = True
        state.death_flashes.append(
            {"x": inimigo.x, "y": inimigo.y, "timer": 0.3, "color": (255, 50, 255)}
        )
    state.enemies.clear()
    state.projectiles.clear()

    # Todas as torres assumem o sprite "speed8" (se o asset existir).
    try:
        novo = pygame.transform.smoothscale(assets.get("speed8"), (56, 56))
    except KeyError:
        logger.warning("Asset 'speed8' ausente: sprites das torres mantidos.")
    else:
        for torre in state.towers:
            torre.sprite = novo

    state.map_grayscale = True


def _encerrar_efeito_speed7(state: GameState, assets, audio) -> None:
    """Reverte o efeito do Speed7: música retoma, sprites e mapa ao normal."""
    audio.encerrar_suspense()  # retoma a música de fundo de onde parou
    state.map_grayscale = False
    # Restaura o sprite original de cada torre (recarrega pelo asset_name).
    for torre in state.towers:
        # Speed5 com buff ativo deve voltar para o sprite de buff (speed6), não
        # para o base — delega à própria torre.
        if isinstance(torre, Speed5):
            torre.refresh_sprite()
            continue
        try:
            torre.sprite = pygame.transform.smoothscale(
                assets.get(torre.asset_name), (SPRITE_SIZE, SPRITE_SIZE)
            )
        except KeyError:
            pass  # asset ausente: mantém o sprite atual


def _atualizar_skip(dt: float, state: GameState) -> None:
    """Controla o aparecimento do Skip durante a wave e o Auto-Skip.

    O Skip é armado quando a wave fica ativa (limiar sorteado 15–20s); fica
    disponível após o limiar se ainda há inimigos. Com Auto-Skip ligado, aciona
    sozinho após 3s. Entre waves, desarma. Usa tempo de jogo (dt já com 2×).
    """
    wm = state.wave_manager
    # A wave conta como "em andamento" enquanto ainda há inimigos no campo —
    # `wave_active` vira False assim que a fila de spawns esvazia (todos
    # invocados), mas o combate continua. Sem isto o Skip nunca apareceria nas
    # ondas cujo spawn termina antes do limiar de 15–20s.
    em_andamento = wm.wave_active or bool(state.enemies)
    if em_andamento:
        if state.skip_threshold <= 0.0:
            state.skip_threshold = random.uniform(15.0, 20.0)
            state.skip_timer = 0.0
            state.skip_disponivel = False
            state.auto_skip_timer = 3.0
        state.skip_timer += dt
        if state.skip_timer >= state.skip_threshold and state.enemies:
            state.skip_disponivel = True
        if state.skip_disponivel and state.auto_skip:
            state.auto_skip_timer -= dt
            if state.auto_skip_timer <= 0.0:
                _executar_skip(state)
    else:
        state.skip_threshold = 0.0
        state.skip_disponivel = False


def _skip_bonus(state: GameState) -> int:
    """Bônus do Skip: 1/4 das recompensas dos inimigos restantes na wave."""
    return sum(e.reward for e in state.enemies) // 4


def _executar_skip(state: GameState) -> None:
    """Executa o Skip: bônus e avança para a próxima wave imediatamente.

    Inimigos em campo PERMANECEM — a nova wave spawna por cima deles.
    O bônus (1/4 das recompensas dos inimigos vivos) compensa o jogador
    por avançar sem esperar o intervalo entre ondas.
    """
    if not state.skip_disponivel:
        return
    state.coins += _skip_bonus(state)
    wm = state.wave_manager
    if wm.wave_active:
        wm.forcar_fim_onda()   # ainda spawnando: encerra e avança
    else:
        # Spawn terminou mas o intervalo ainda está contando: zera a espera.
        wm.wave_timer = 0.0
    state.skip_disponivel = False
    state.skip_threshold = 0.0
    state.skip_timer = 0.0


def _atualizar_jogo(dt: float, state: GameState, waypoints: list[dict], assets) -> None:
    """Atualiza torres, projéteis, inimigos, flashes e ondas (apenas PLAYING)."""
    # 1. Torres miram e disparam.
    for torre in state.towers:
        torre.aoe_flash = None
        projetil = torre.update(dt, state.enemies)
        if projetil is not None:
            if isinstance(projetil, list):
                state.projectiles.extend(projetil)
            else:
                state.projectiles.append(projetil)
        if torre.aoe_flash:
            cx, cy = torre.centro_pixel()
            fl = torre.aoe_flash
            state.aoe_flashes.append({
                "x": cx, "y": cy,
                "raio": fl["raio"], "timer": fl["dur"], "max": fl["dur"],
                "cor": fl["cor"],
            })

    # 2. Projéteis se movem e resolvem colisão.
    for proj in state.projectiles[:]:
        if proj.update(dt):
            if not proj.target.is_dead():
                if isinstance(proj.target, Ancelotti):
                    # Stun (15%) e possível invocação de Labubu MUI (20%),
                    # encapsulados no boss. Sem dano duplicado (receber_dano já
                    # aplica o dano).
                    if random.random() < proj.target.stun_chance:
                        proj.target.apply_stun(1.5)
                    mui = proj.target.receber_dano(
                        proj.damage, state.wave, assets, waypoints
                    )
                    if mui is not None:
                        state.enemies.append(mui)
                else:
                    proj.target.hp -= proj.damage
                    if proj.apply_slow:
                        proj.target.apply_slow(2.0)
            state.projectiles.remove(proj)

    # 3. Inimigos: fim do path tira vida; mortos dão moedas + flash.
    for enemy in state.enemies[:]:
        result = enemy.update(dt, waypoints)
        # Ancelotti retorna (reached_end, spawn|None); inimigos normais, bool.
        if isinstance(result, tuple):
            reached_end, spawned = result
        else:
            reached_end, spawned = result, None

        if spawned is not None:
            state.enemies.append(spawned)
            # Flash amarelo sinalizando o reforço invocado.
            state.death_flashes.append(
                {"x": enemy.x, "y": enemy.y, "timer": 0.5,
                 "color": (255, 200, 0), "max": 0.5}
            )

        if reached_end:
            state.lives -= enemy.damage_to_base
            state.enemies.remove(enemy)
            state.projectiles = [p for p in state.projectiles if p.target is not enemy]
        elif enemy.is_dead():
            state.coins += enemy.reward
            state.enemies.remove(enemy)
            state.projectiles = [p for p in state.projectiles if p.target is not enemy]
            state.death_flashes.append({"x": enemy.x, "y": enemy.y, "timer": 0.3})
            state.kills += 1
            if enemy.name == "Ancelotti":
                state.boss_defeated = True

    # 4. Flashes de morte expiram.
    for flash in state.death_flashes[:]:
        flash["timer"] -= dt
        if flash["timer"] <= 0.0:
            state.death_flashes.remove(flash)

    # 4b. AOE flashes (anéis expansivos) expiram.
    for fl in state.aoe_flashes[:]:
        fl["timer"] -= dt
        if fl["timer"] <= 0.0:
            state.aoe_flashes.remove(fl)

    # 5. Gerenciador de ondas (congelado enquanto seletor de dificuldade ativo).
    if not state.waves_congeladas:
        state.wave_manager.update(dt, state.enemies, waypoints)
    state.wave = state.wave_manager.display_wave()


def _desenhar_mundo(tela, game_map, state, fonte_dev, dev, grid):
    """Desenha mapa, torres, projéteis, flashes e inimigos."""
    game_map.draw(tela)

    # O caminho NÃO é desenhado aqui: fica invisível até o jogador selecionar
    # uma carta (overlay verde + trilha vermelha no bloco de render do main).
    # No modo dev o grid de debug ainda realça as células PATH.

    for torre in state.towers:
        torre.draw(tela)

    for proj in state.projectiles:
        proj.draw(tela)

    # AOE flashes: anéis expansivos (slow azul / buff amarelo).
    for fl in state.aoe_flashes:
        t = fl["timer"] / max(0.001, fl["max"])   # 1.0→0.0 (some going down)
        raio = int(fl["raio"] * (1.0 - t))        # expande do centro para fora
        alpha = int(200 * t)
        if raio > 2:
            sz = raio * 2 + 4
            fx = pygame.Surface((sz, sz), pygame.SRCALPHA)
            pygame.draw.circle(fx, (*fl["cor"], alpha), (raio + 2, raio + 2), raio, 3)
            tela.blit(fx, (int(fl["x"]) - raio - 2, int(fl["y"]) - raio - 2))

    # Flashes (morte = vermelho; spawn de reforço = amarelo).
    for flash in state.death_flashes:
        dur = flash.get("max", 0.3)
        cor = flash.get("color", (230, 40, 40))
        raio = int(20 * (flash["timer"] / dur))
        if raio > 0:
            fx = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
            pygame.draw.circle(fx, (*cor, 150), (raio, raio), raio)
            tela.blit(fx, (int(flash["x"]) - raio, int(flash["y"]) - raio))

    for enemy in state.enemies:
        enemy.draw(tela)

    if dev:
        grid.draw_debug(tela)
        for torre in state.towers:
            torre.draw_range(tela)
        for enemy in state.enemies:
            enemy.draw_debug(tela, fonte_dev)
        # Contador de entidades (ciano, sem fundo).
        contador = fonte_dev.render(
            f"Inimigos: {len(state.enemies)} | Torres: {len(state.towers)} "
            f"| Projéteis: {len(state.projectiles)}",
            True,
            COR_CIANO,
        )
        tela.blit(contador, (MAP_RECT.x + 8, MAP_RECT.y + 34))


def _desenhar_hitboxes_torres(tela: pygame.Surface, towers: list) -> None:
    """Círculo de hitbox (HIT_RADIUS) de cada torre durante posicionamento de carta.

    Mostra visualmente onde está o "corpo" de cada torre — dois círculos que
    se tocam = sobreposição proibida. Cor dourada semi-transparente.
    """
    raio = int(HIT_RADIUS)
    tamanho = raio * 2 + 4
    surf = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255, 208, 64, 50),  (raio + 2, raio + 2), raio)
    pygame.draw.circle(surf, (255, 208, 64, 210), (raio + 2, raio + 2), raio, 2)
    for t in towers:
        cx, cy = t.centro_pixel()
        tela.blit(surf, (cx - raio - 2, cy - raio - 2))


def _desenhar_preview(tela, state, grid, preview_surf: pygame.Surface) -> None:
    """Círculo de range da torre selecionada, centrado no cursor.

    Verde se a posição está livre para posicionamento; vermelho se bloqueada
    (PATH ou OCCUPIED). Surface reutilizada — limpa antes de desenhar.
    """
    mx, my = to_render(pygame.mouse.get_pos())
    if not MAP_RECT.collidepoint(mx, my):
        return

    tipo_sel = TOWER_TYPES[state.selected_card]
    placeable = grid.is_placeable(mx, my)
    # Verifica também sobreposição com torres existentes.
    sem_sobreposicao = all(
        (mx - t.x) ** 2 + (my - t.y) ** 2 > (2 * HIT_RADIUS) ** 2
        for t in state.towers
    )
    valido = placeable and sem_sobreposicao
    cor_rgb = COR_OVERLAY_VALIDO if valido else COR_OVERLAY_INVALIDO

    # Alcance "simbólico" (ex.: Speed7, habilidade global) não desenha círculo.
    if tipo_sel.range_px <= max(WINDOW_WIDTH, WINDOW_HEIGHT):
        preview_surf.fill((0, 0, 0, 0))
        pygame.draw.circle(preview_surf, (*cor_rgb, ALPHA_OVERLAY_HOVER), (mx, my), tipo_sel.range_px)
        tela.blit(preview_surf, (0, 0))

    # Hitbox do cursor: círculo de HIT_RADIUS mostrando o "corpo" da torre.
    raio_hit = int(HIT_RADIUS)
    hit_size = raio_hit * 2 + 4
    hit_surf = pygame.Surface((hit_size, hit_size), pygame.SRCALPHA)
    pygame.draw.circle(hit_surf, (*cor_rgb, 80),  (raio_hit + 2, raio_hit + 2), raio_hit)
    pygame.draw.circle(hit_surf, (*cor_rgb, 230), (raio_hit + 2, raio_hit + 2), raio_hit, 2)
    tela.blit(hit_surf, (mx - raio_hit - 2, my - raio_hit - 2))


def _definir_cursor(cursor) -> None:
    """Define o cursor do sistema, ignorando plataformas sem suporte (headless)."""
    try:
        pygame.mouse.set_cursor(cursor)
    except pygame.error:
        pass


def _atualizar_cursor(state_manager, state, card_hand) -> None:
    """Define o cursor conforme o contexto (apenas em jogo)."""
    if state_manager.current != GameScreen.PLAYING:
        _definir_cursor(pygame.SYSTEM_CURSOR_ARROW)
        return

    mx, my = to_render(pygame.mouse.get_pos())
    if state.selected_card is not None and MAP_RECT.collidepoint(mx, my):
        _definir_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
    elif HUD_RECT.collidepoint(mx, my) and card_hand.handle_click((mx, my)) is not None:
        _definir_cursor(pygame.SYSTEM_CURSOR_HAND)
    else:
        _definir_cursor(pygame.SYSTEM_CURSOR_ARROW)


if __name__ == "__main__":
    main()
