"""Pacote entities — registra torres extras que causariam import circular em tower.py.

DrivingCarSpeed herda de Tower (definida em tower.py), portanto importá-la dentro
de tower.py geraria um ciclo. A solução é importá-la aqui e adicionar à lista
TOWER_TYPES em-place (mutação da lista), garantindo que todos os callers que já
importaram `from entities.tower import TOWER_TYPES` vejam a versão atualizada.
"""

from entities.tower import TOWER_TYPES  # noqa: F401 — importado para permitir mutação
from entities.driving_car_speed import DrivingCarSpeed  # noqa: F401

# Adiciona DrivingCarSpeed ao final da lista de torres jogáveis.
# Mutação em-place: todos os módulos que fizeram
# `from entities.tower import TOWER_TYPES` apontam para o mesmo objeto.
if DrivingCarSpeed not in TOWER_TYPES:
    TOWER_TYPES.append(DrivingCarSpeed)
