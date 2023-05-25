import logging
import asyncio
from typing import (Any, Awaitable, BinaryIO, Callable, Dict, List, Optional,
                    Tuple, Type, Union)
import uuid

class OutageHandler:
    def __init__(self, client_uuid, interval) -> None:
        self._log = logging.getLogger()
        self._client_uuid = client_uuid
        self._interval = _interval

    async def send_email():
        self._log.info('TODO: Send email')

    async def run(self):
        while True:
            await self.send_email()
            await asyncio.sleep(self._interval)

