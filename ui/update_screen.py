"""Telas do fluxo de auto-update (Pygame puro, sem pygame_gui).

São desenhadas na render_surface (1280×720) como qualquer outra tela. Não
mexem no estado do jogo: o main.py as exibe em mini-loops durante a verificação
e o download, e usa `UpdateResultScreen` para o resultado final.
"""

import pygame
from core.asset_manager import AssetManager

from config.settings import (
    COLOR_GOLD,
    COLOR_HUD_BG,
    COR_TEXTO,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    COR_FUNDO_MODAL,
    COR_BORDA_MODAL,
    COR_BORDA_MODAL_TOPO,
    COR_HUD_BORDA,
    COR_DOURADO,
    COR_LABEL_HUD,
)

CENTRO_X: int = WINDOW_WIDTH // 2
CENTRO_Y: int = WINDOW_HEIGHT // 2


class UpdateCheckScreen:
    """Tela "Verificando atualizações..." com reticências animadas."""

    def __init__(self) -> None:
        self._fonte = AssetManager.get_font("font_title", 48)

    def draw(self, surface: pygame.Surface) -> None:
        """Fundo preto + texto centralizado com 0–3 pontos piscando."""
        surface.fill((0, 0, 0))
        pontos = "." * (1 + (pygame.time.get_ticks() // 400) % 3)
        txt = self._fonte.render(f"Verificando atualizações{pontos}", True, COR_TEXTO)
        surface.blit(txt, txt.get_rect(center=(CENTRO_X, CENTRO_Y)))


class UpdateProgressScreen:
    """Barra de progresso do download (Pygame puro)."""

    BAR_W: int = 600
    BAR_H: int = 36

    def __init__(self, nova_versao: str | None = None) -> None:
        self._fonte_titulo = AssetManager.get_font("font_title", 56)
        self._fonte = AssetManager.get_font("font_title", 32)
        self._fonte_peq = AssetManager.get_font("font_title", 26)
        self._nova_versao = nova_versao

    def draw(
        self, surface: pygame.Surface, bytes_baixados: int, total_bytes: int
    ) -> None:
        """Título, MB baixados/total, barra de progresso e aviso."""
        surface.fill((0, 0, 0))

        titulo = self._fonte_titulo.render("ATUALIZANDO...", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, CENTRO_Y - 120)))

        mb_baixados = bytes_baixados / 1_000_000
        mb_total = total_bytes / 1_000_000
        if total_bytes > 0:
            texto = f"Baixando atualização... {mb_baixados:.1f} MB / {mb_total:.1f} MB"
        else:
            texto = f"Baixando atualização... {mb_baixados:.1f} MB"
        arq = self._fonte.render(texto, True, COR_TEXTO)
        surface.blit(arq, arq.get_rect(center=(CENTRO_X, CENTRO_Y - 50)))

        # Barra de progresso (fração = bytes_baixados/total_bytes).
        fracao = (bytes_baixados / total_bytes) if total_bytes > 0 else 0.0
        fracao = max(0.0, min(1.0, fracao))
        barra = pygame.Rect(0, 0, self.BAR_W, self.BAR_H)
        barra.center = (CENTRO_X, CENTRO_Y)
        pygame.draw.rect(surface, (40, 40, 50), barra, border_radius=6)
        preenchida = pygame.Rect(barra.x, barra.y, int(self.BAR_W * fracao), self.BAR_H)
        pygame.draw.rect(surface, COLOR_GOLD, preenchida, border_radius=6)
        pygame.draw.rect(surface, COR_TEXTO, barra, 2, border_radius=6)

        aviso = self._fonte.render("Não feche o jogo", True, (230, 80, 80))
        surface.blit(aviso, aviso.get_rect(center=(CENTRO_X, CENTRO_Y + 70)))

        if self._nova_versao:
            v = self._fonte_peq.render(
                f"Nova versão: {self._nova_versao}", True, COR_TEXTO
            )
            surface.blit(v, v.get_rect(bottomright=(WINDOW_WIDTH - 20, WINDOW_HEIGHT - 20)))


class UpdateResultScreen:
    """Tela de resultado do update, fechável por clique/tecla.

    `result_type` ∈ {"updated", "current", "error", "not_configured"}.
    """

    _MENSAGENS = {
        "updated": ("✅ Atualizado com sucesso!", (80, 220, 90)),
        "current": ("✅ Você já tem a versão mais recente", (80, 220, 90)),
        "error": ("❌ Falha ao atualizar. Tente mais tarde.", (220, 60, 60)),
        "not_configured": ("⚠️ Atualizações não configuradas.", COLOR_GOLD),
    }

    def __init__(
        self,
        manager=None,
        result_type: str = "current",
        version: str | None = None,
        changelog: str | None = None,
    ) -> None:
        # `manager` mantido por compatibilidade de assinatura; não é usado
        # (a tela é desenhada em Pygame puro, sem elementos pygame_gui).
        self._tipo = result_type
        self._version = version
        self._changelog = changelog
        self._fonte_header = AssetManager.get_font("font_title", 22)
        self._fonte = AssetManager.get_font("font_body", 20)
        self._fonte_peq = AssetManager.get_font("font_body", 15)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Retorna True quando o jogador fecha (clique ou qualquer tecla)."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            return True
        if event.type == pygame.KEYDOWN:
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Painel modal com resultado da atualização e changelog."""
        surface.fill((10, 10, 6))
        painel = pygame.Rect(0, 0, 560, 400)
        painel.center = (CENTRO_X, CENTRO_Y)

        pygame.draw.rect(surface, COR_FUNDO_MODAL, painel)
        pygame.draw.rect(surface, COR_BORDA_MODAL, painel, 1)
        pygame.draw.line(surface, COR_BORDA_MODAL_TOPO,
                         painel.topleft, (painel.right, painel.top), 3)
        header_y = painel.y + 50
        pygame.draw.line(surface, COR_HUD_BORDA,
                         (painel.x, header_y), (painel.right, header_y), 1)
        grad = pygame.Surface((painel.width // 2, 50), pygame.SRCALPHA)
        grad.fill((255, 208, 64, 10))
        surface.blit(grad, painel.topleft)
        hdr = self._fonte_header.render("ATUALIZAÇÃO", True, COR_DOURADO)
        surface.blit(hdr, (painel.x + 20, painel.y + 15))

        msg, cor = self._MENSAGENS.get(self._tipo, self._MENSAGENS["current"])
        msg_surf = self._fonte.render(msg, True, cor)
        surface.blit(msg_surf, msg_surf.get_rect(center=(CENTRO_X, painel.y + 80)))

        if self._version:
            v = self._fonte_peq.render(f"versão {self._version}", True, COR_LABEL_HUD)
            surface.blit(v, v.get_rect(center=(CENTRO_X, painel.y + 114)))

        if self._changelog:
            linhas = self._changelog.split("\n")[:7]
            y = painel.y + 148
            for linha in linhas:
                txt = self._fonte_peq.render(f"— {linha}", True, COR_TEXTO)
                surface.blit(txt, (painel.x + 24, y))
                y += 26

        rodape = self._fonte_peq.render(
            "clique ou pressione qualquer tecla", True, COR_LABEL_HUD
        )
        surface.blit(rodape, rodape.get_rect(center=(CENTRO_X, painel.bottom - 30)))

    def destroy(self) -> None:
        """Sem elementos pygame_gui para remover (no-op por simetria de API)."""
