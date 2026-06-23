"""Carregamento e cache central de assets.

Regra de arquitetura: nenhum asset é carregado fora desta classe. Todas as
imagens são lidas uma única vez no boot e cacheadas em memória. Entidades e
UI recuperam Surfaces via `AssetManager.get(nome)`, nunca com
`pygame.image.load()` direto.
"""

import logging
from pathlib import Path

import pygame

from config.settings import ASSETS_DIR

logger = logging.getLogger(__name__)


class AssetManager:
    """Cache único de imagens carregadas do diretório `assets/`.

    Cada imagem é registrada sob uma chave **qualificada** `"pasta/nome"`
    (sempre única), em minúsculas. Ex.: `assets/speeds/speed1.png` ->
    `"speeds/speed1"`. Para conveniência, também é criado um alias com o nome
    simples (`Path.stem`) — mas apenas quando esse nome é único em todo o
    `assets/`. Se o mesmo nome existir em pastas diferentes (ex.: dois
    `ancelotti.png`), o alias simples é omitido: o nome é ambíguo e deve ser
    acessado pela chave qualificada (`get("labubus/ancelotti")`).
    """

    def __init__(self, assets_dir: Path = ASSETS_DIR) -> None:
        self._assets_dir: Path = assets_dir
        self._imagens: dict[str, pygame.Surface] = {}

    def carregar_tudo(self) -> None:
        """Varre `assets/` recursivamente e carrega todas as imagens .png.

        Deve ser chamado após `pygame.display.set_mode()`, pois usa
        `convert_alpha()`, que exige um display de vídeo inicializado.
        Levanta `FileNotFoundError` se o diretório de assets não existir.
        """
        if not self._assets_dir.is_dir():
            raise FileNotFoundError(
                f"Diretório de assets não encontrado: {self._assets_dir}"
            )

        # Nomes simples vistos mais de uma vez (ambíguos) não recebem alias.
        stems_ambiguos: set[str] = set()

        for caminho in sorted(self._assets_dir.rglob("*.png")):
            chave_qual = f"{caminho.parent.name}/{caminho.stem}".lower()
            try:
                surface = pygame.image.load(caminho).convert_alpha()
            except pygame.error as erro:
                raise RuntimeError(
                    f"Falha ao carregar asset '{caminho}': {erro}"
                ) from erro

            self._imagens[chave_qual] = surface

            # Alias com nome simples — só se ainda único.
            stem = caminho.stem.lower()
            if stem in stems_ambiguos:
                continue  # já marcado como ambíguo: sem alias
            if stem in self._imagens:
                # Segunda ocorrência do mesmo nome: remove o alias e marca ambíguo.
                # Condição conhecida e tratada (ex.: ancelotti em dialogs/ e labubus/),
                # por isso é informativa, não um alerta de anomalia.
                logger.info(
                    "Nome de asset ambíguo '%s' (em pastas diferentes); "
                    "use a chave qualificada 'pasta/%s'.",
                    stem,
                    stem,
                )
                del self._imagens[stem]
                stems_ambiguos.add(stem)
            else:
                self._imagens[stem] = surface

        logger.info("Assets carregados: %d imagens", len(self))

    # Assets esperados pelo jogo (relativos a `assets/`). Ausências apenas geram
    # aviso PT-BR — o jogo segue com placeholders/fallbacks, nunca quebra.
    ASSETS_ESPERADOS: tuple[str, ...] = (
        "dialogs/victory_image.png",
        "sounds/sound.mp3",
        "audio/killthatboy.mp3",
        "audio/suspensemusic.mp3",
        "speeds/speed5.png",
        "speeds/speed6.png",
        "speeds/speed7.png",
        "speeds/speed8.png",
    )

    def verificar_assets_esperados(self) -> list[str]:
        """Checa via `Path.exists()` os assets esperados; loga aviso PT-BR.

        Não levanta erro: retorna a lista de relativos ausentes para referência.
        Nenhum asset é carregado aqui — apenas verificação de existência.
        """
        ausentes: list[str] = []
        for relativo in self.ASSETS_ESPERADOS:
            if not (self._assets_dir / relativo).exists():
                ausentes.append(relativo)
                logger.warning(
                    "Asset esperado ausente: assets/%s "
                    "(o jogo segue com placeholder/fallback).",
                    relativo,
                )
        if not ausentes:
            logger.info("Todos os assets esperados estão presentes.")
        return ausentes

    def get(self, nome: str) -> pygame.Surface:
        """Retorna a Surface cacheada da imagem `nome` (sem extensão).

        Levanta `KeyError` se o asset não foi carregado.
        """
        chave = nome.lower()
        if chave not in self._imagens:
            raise KeyError(
                f"Asset '{nome}' não encontrado no cache. "
                f"Disponíveis: {sorted(self._imagens)}"
            )
        return self._imagens[chave]

    def __len__(self) -> int:
        """Quantidade de imagens distintas em cache (chaves qualificadas)."""
        return sum(1 for chave in self._imagens if "/" in chave)
