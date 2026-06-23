"""Telas do fluxo de auto-update (Pygame puro, sem pygame_gui).

São desenhadas na render_surface (1280×720) como qualquer outra tela. Não
mexem no estado do jogo: o main.py as exibe em mini-loops durante a verificação
e o download, e usa `UpdateResultScreen` para o resultado final.
"""

import pygame

from config.settings import (
    COLOR_GOLD,
    COLOR_HUD_BG,
    COR_TEXTO,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)

CENTRO_X: int = WINDOW_WIDTH // 2
CENTRO_Y: int = WINDOW_HEIGHT // 2


class UpdateCheckScreen:
    """Tela "Verificando atualizações..." com reticências animadas."""

    def __init__(self) -> None:
        self._fonte = pygame.font.SysFont(None, 48)

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
        self._fonte_titulo = pygame.font.SysFont(None, 56, bold=True)
        self._fonte = pygame.font.SysFont(None, 32)
        self._fonte_peq = pygame.font.SysFont(None, 26)
        self._nova_versao = nova_versao

    def draw(
        self, surface: pygame.Surface, filename: str, current: int, total: int
    ) -> None:
        """Título, arquivo atual, barra de progresso e aviso."""
        surface.fill((0, 0, 0))

        titulo = self._fonte_titulo.render("ATUALIZANDO...", True, COLOR_GOLD)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, CENTRO_Y - 120)))

        arq = self._fonte.render(
            f"Baixando: {filename}  ({current}/{total})", True, COR_TEXTO
        )
        surface.blit(arq, arq.get_rect(center=(CENTRO_X, CENTRO_Y - 50)))

        # Barra de progresso (fração = current/total).
        fracao = (current / total) if total > 0 else 0.0
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
        self._fonte_titulo = pygame.font.SysFont(None, 52, bold=True)
        self._fonte = pygame.font.SysFont(None, 32)
        self._fonte_peq = pygame.font.SysFont(None, 26)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Retorna True quando o jogador fecha (clique ou qualquer tecla)."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            return True
        if event.type == pygame.KEYDOWN:
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Mensagem central conforme o tipo + changelog (se houver)."""
        surface.fill(COLOR_HUD_BG)
        msg, cor = self._MENSAGENS.get(self._tipo, self._MENSAGENS["current"])

        titulo = self._fonte_titulo.render(msg, True, cor)
        surface.blit(titulo, titulo.get_rect(center=(CENTRO_X, CENTRO_Y - 140)))

        if self._version:
            v = self._fonte.render(f"Versão: {self._version}", True, COR_TEXTO)
            surface.blit(v, v.get_rect(center=(CENTRO_X, CENTRO_Y - 90)))

        # Changelog (uma linha por item, quebrado por \n).
        if self._changelog:
            linhas = self._changelog.split("\n")
            y = CENTRO_Y - 40
            for linha in linhas:
                txt = self._fonte_peq.render(linha, True, COR_TEXTO)
                surface.blit(txt, txt.get_rect(center=(CENTRO_X, y)))
                y += 32

        rodape = self._fonte_peq.render(
            "Clique ou pressione qualquer tecla para continuar", True, COLOR_GOLD
        )
        surface.blit(rodape, rodape.get_rect(center=(CENTRO_X, WINDOW_HEIGHT - 60)))

    def destroy(self) -> None:
        """Sem elementos pygame_gui para remover (no-op por simetria de API)."""
