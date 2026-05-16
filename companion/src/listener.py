"""Base abstrata pra cada listener async (dbus, claude, backup)."""
from __future__ import annotations

import abc
import logging

log = logging.getLogger(__name__)


class Listener(abc.ABC):
    """Cada listener implementa run() async em loop infinito."""

    name: str = "listener"

    @abc.abstractmethod
    async def run(self) -> None:
        """Loop principal. Não retorna até cancelamento."""
        ...

    async def healthcheck(self) -> bool:
        """Override pra checks específicos. Default: sempre vivo."""
        return True
