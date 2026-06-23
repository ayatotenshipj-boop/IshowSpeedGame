"""Entrypoint do jogo Speed Vs Labubu.

Inicializa o pygame, abre a janela e roda o game loop principal a 60 FPS em
torno de um StateManager (Menu → Jogo → Pausa → Game Over / Vitória). A flag
`--dev` ativa o modo desenvolvimento (grid, alcances, posições e FPS no título).

Uso:
    python main.py          # modo normal
    python main.py --dev    # modo dev
"""

import logging
import sys
import threading

import pygame
import pygame_gui

from config.settings import (
    COLOR_HUD_BG,
    FPS,
    HIT_RADIUS,
    HUD_RECT,
    MAP_RECT,
    MAX_PER_TYPE,
    RENDER_HEIGHT,
    RENDER_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from core.asset_manager import AssetManager
from core.audio import AudioManager
from core.game_state import GameState
from core.state_manager import GameScreen, StateManager
from core.updater import Updater
from entities.tower import TOWER_TYPES, Speed6, Speed7
from entities.wave_manager import WAVES
from map.game_map import GameMap
from map.placement_grid import PlacementGrid
from ui.card_hand import CardHand
from ui.hud import HUD
from ui.intro_scene import IntroScene
from ui.menus import GameOverScreen, MenuScreen, PauseScreen, VictoryScreen
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
        render_surface.fill((0, 0, 0))
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
        render_surface.fill((0, 0, 0))
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

    # 2) Há atualização: baixar os arquivos com barra de progresso.
    progress_screen = UpdateProgressScreen(remote.get("version"))

    def _progresso(arquivo: str, indice: int, total: int) -> None:
        _atualizar_escala(tela)
        render_surface.fill((0, 0, 0))
        progress_screen.draw(render_surface, arquivo, indice, total)
        _apresentar(tela, render_surface)
        pygame.event.pump()  # mantém a janela responsiva durante o download

    arquivos = remote.get("files", [])
    sucesso = updater.download_files(arquivos, _progresso) if arquivos else True

    if sucesso:
        updater.save_local_version(remote)
        _mostrar_resultado_update(
            UpdateResultScreen(
                None,
                "updated",
                version=remote.get("version"),
                changelog=updater.get_changelog(remote),
            ),
            tela,
            render_surface,
            clock,
        )
        updater.restart_game()  # reinicia para aplicar os arquivos baixados
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
    ui_manager = pygame_gui.UIManager((RENDER_WIDTH, RENDER_HEIGHT))
    state_manager = StateManager()
    current_screen = MenuScreen(ui_manager, assets)
    updater = Updater()  # auto-update via GitHub raw (botão "Atualizar" no menu)
    # Música de fundo inicia uma vez no boot e segue tocando por menu/intro/jogo
    # (não reinicia ao começar a partida — evita a música "tocar de novo").
    audio.iniciar_fundo()

    def reset_game() -> None:
        """Reinicia o estado da partida (GameState/grid/cartas).

        NÃO mexe na música: ela já está tocando desde o menu e deve continuar
        contínua até a partida (evita reinício ao clicar em JOGAR). A restauração
        da música é feita só nas transições de tela (menu/fim de jogo).
        """
        nonlocal state, grid
        state = GameState()
        state.wave_manager.assets = assets
        grid = PlacementGrid()
        card_hand.deselect()

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
                acao = current_screen.handle_event(evento)
                if acao == "play":
                    # JOGAR: prepara a partida e exibe a intro antes do jogo.
                    current_screen.destroy()
                    reset_game()
                    current_screen = IntroScene(assets)
                    state_manager.transition(GameScreen.INTRO)
                elif acao == "quit":
                    rodando = False
                elif acao == "update":
                    # Verifica/baixa atualização (mini-loops próprios). Ao voltar,
                    # o loop principal continua desenhando o menu normalmente.
                    _executar_fluxo_update(updater, tela, render_surface, clock)

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
                        # 0) Botões do HUD (velocidade 2× e pular onda) têm
                        # prioridade máxima — evitam posicionar torre por baixo.
                        if hud.speed_button_rect().collidepoint(pos):
                            state.speed_multiplier = (
                                1.0 if state.speed_multiplier >= 2.0 else 2.0
                            )
                            continue
                        if (
                            state.wave_manager.time_to_next_wave() is not None
                            and hud.skip_button_rect().collidepoint(pos)
                        ):
                            restante = state.wave_manager.skip_wave()
                            state.coins += hud.skip_bonus(restante)
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
                            # Sem carta: clique numa torre abre o painel; vazio fecha.
                            cx, cy = grid.pixel_to_cell(*pos)
                            state.selected_tower = next(
                                (t for t in state.towers if t.cell_x == cx and t.cell_y == cy),
                                None,
                            )
                        elif MAP_RECT.collidepoint(pos) and state.selected_card is not None:
                            idx = state.selected_card
                            tipo = TOWER_TYPES[idx]
                            # Posicionamento livre: a torre fica no pixel exato do
                            # clique. O grid só valida a célula central (PATH/ocupada).
                            click_x, click_y = pos
                            cx, cy = grid.pixel_to_cell(click_x, click_y)
                            n_tipo = sum(1 for t in state.towers if type(t) is tipo)
                            # Hitbox reduzida: rejeita sobreposição com outra torre
                            # (distância entre centros <= 2*HIT_RADIUS).
                            sem_sobreposicao = all(
                                (click_x - t.x) ** 2 + (click_y - t.y) ** 2
                                > (2 * HIT_RADIUS) ** 2
                                for t in state.towers
                            )
                            if (
                                grid.is_area_placeable(click_x, click_y, tipo.cell_radius)
                                and sem_sobreposicao
                                and state.coins >= tipo.cost
                                and n_tipo < MAX_PER_TYPE
                            ):
                                state.towers.append(
                                    tipo(assets, click_x, click_y, cx, cy)
                                )
                                state.coins -= tipo.cost
                                grid.set_occupied_radius(cx, cy, tipo.cell_radius)
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
                    current_screen = MenuScreen(ui_manager, assets)
                    state_manager.transition(GameScreen.MENU)

            elif state_manager.current in (GameScreen.GAME_OVER, GameScreen.VICTORY):
                acao = current_screen.handle_event(evento)
                if acao == "retry":
                    current_screen.destroy()
                    current_screen = None
                    reset_game()
                    state_manager.transition(GameScreen.PLAYING)
                elif acao == "menu":
                    current_screen.destroy()
                    audio.parar()
                    audio.iniciar_fundo()  # restaura música de fundo no menu
                    current_screen = MenuScreen(ui_manager, assets)
                    state_manager.transition(GameScreen.MENU)

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

        if state_manager.current == GameScreen.PLAYING:
            _atualizar_jogo(dt_efetivo, state, waypoints)
            card_hand.update(dt, to_render(pygame.mouse.get_pos()))  # hover (real)

            # Checa derrota.
            if state.lives <= 0:
                # Restaura música de fundo (corta o loop de suspense do Speed7).
                audio.parar()
                audio.iniciar_fundo()
                state_manager.transition(GameScreen.GAME_OVER)
                current_screen = GameOverScreen(ui_manager)
            # Checa vitória (ondas concluídas, sem inimigos e boss derrotado).
            elif (
                state.wave_manager.is_finished()
                and not state.enemies
                and state.boss_defeated
            ):
                # Restaura música de fundo (corta o loop de suspense do Speed7).
                audio.parar()
                audio.iniciar_fundo()
                state_manager.transition(GameScreen.VICTORY)
                current_screen = VictoryScreen(
                    ui_manager, state.kills, state.coins, victory_image
                )

        # Cursor conforme o contexto (apenas em jogo).
        _atualizar_cursor(state_manager, state, card_hand)

        # --- Render --- (tudo desenhado na Surface interna render_surface)
        render_surface.fill(COLOR_HUD_BG)

        if state_manager.current in (GameScreen.PLAYING, GameScreen.PAUSED):
            _desenhar_mundo(
                render_surface, game_map, state,
                fonte_dev, dev and state_manager.current == GameScreen.PLAYING, grid,
            )
            # Tom acinzentado sobre o mapa após a habilidade do Speed7.
            if state.map_grayscale:
                cinza = pygame.Surface(MAP_RECT.size, pygame.SRCALPHA)
                cinza.fill((128, 128, 128, 120))
                render_surface.blit(cinza, MAP_RECT.topleft)
            # Overlays de posicionamento (somente em jogo, com carta selecionada):
            # verde onde pode posicionar; trilha vermelha forte onde não pode.
            if (
                state_manager.current == GameScreen.PLAYING
                and state.selected_card is not None
            ):
                overlay_free = pygame.Surface(MAP_RECT.size, pygame.SRCALPHA)
                overlay_free.fill((50, 200, 50, 45))
                render_surface.blit(overlay_free, MAP_RECT.topleft)
                grid.draw_path(
                    render_surface,
                    pygame.time.get_ticks() / 1000.0,
                    color=(200, 40, 40),
                    alpha=140,
                )
                # Preview de alcance + highlight da célula sob o cursor, por cima.
                _desenhar_preview(render_surface, state, grid)
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
            )
            # Tooltip da carta sob o cursor (apenas em jogo, por cima de tudo).
            if state_manager.current == GameScreen.PLAYING:
                card_hand.draw_tooltip(render_surface)

        if current_screen is not None:
            current_screen.draw(render_surface)

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
        if isinstance(torre, Speed6):
            torre.activate_buff()
    elif acao == "ability":
        if isinstance(torre, Speed7) and torre.use_ability():
            _ativar_habilidade_speed7(state, assets, audio)
    elif acao == "sell":
        state.coins += torre.sell_refund()
        if torre in state.towers:
            state.towers.remove(torre)
        grid.set_free_radius(torre.cell_x, torre.cell_y, type(torre).cell_radius)
        state.selected_tower = None
    elif acao == "close":
        state.selected_tower = None


def _ativar_habilidade_speed7(state: GameState, assets, audio) -> None:
    """Habilidade global do Speed7: hitkill de todos os inimigos + efeitos.

    - Toca `killthatboy.mp3` SOBREPOSTO (canal próprio, cortado em 1s) sem
      interromper a música de fundo; em paralelo faz crossfade para a música
      de suspense — tudo gerido pelo AudioManager.
    - Elimina todos os inimigos em campo (recompensa, kills e flash roxo).
    - Troca o sprite de todas as torres por `speed8` (56×56).
    - Deixa o mapa acinzentado.
    """
    audio.ativar_killthatboy()
    audio.ativar_suspense()

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


def _atualizar_jogo(dt: float, state: GameState, waypoints: list[dict]) -> None:
    """Atualiza torres, projéteis, inimigos, flashes e ondas (apenas PLAYING)."""
    # 1. Torres miram e disparam.
    for torre in state.towers:
        projetil = torre.update(dt, state.enemies)
        if projetil is not None:
            state.projectiles.append(projetil)

    # 2. Projéteis se movem e resolvem colisão.
    for proj in state.projectiles[:]:
        if proj.update(dt):
            if not proj.target.is_dead():
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
            state.lives -= 1
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

    # 5. Gerenciador de ondas.
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
            (80, 220, 230),
        )
        tela.blit(contador, (MAP_RECT.x + 8, MAP_RECT.y + 34))


def _desenhar_preview(tela, state, grid) -> None:
    """Highlight da célula sob o cursor + círculo de alcance da torre selecionada."""
    mx, my = to_render(pygame.mouse.get_pos())
    if not MAP_RECT.collidepoint(mx, my):
        return

    # Highlight da célula (verde se posicionável, senão vermelho).
    tipo_sel = TOWER_TYPES[state.selected_card]
    rect = grid.cell_rect(mx, my)
    if rect is not None:
        ok = grid.is_area_placeable(mx, my, tipo_sel.cell_radius)
        cor = (50, 255, 50, 80) if ok else (255, 50, 50, 80)
        hl = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        hl.fill(cor)
        tela.blit(hl, rect.topleft)

    # Círculo de alcance centrado no cursor. Alcance "simbólico" (ex.: Speed7,
    # habilidade global) não desenha círculo — seria a tela inteira.
    if tipo_sel.range_px <= max(WINDOW_WIDTH, WINDOW_HEIGHT):
        preview = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(preview, (255, 255, 255, 60), (mx, my), tipo_sel.range_px)
        tela.blit(preview, (0, 0))


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
