# app/db/lazy_session.py
from typing import Optional, Callable

from sqlalchemy.ext.asyncio import AsyncSession


class LazySessionProxy:
    """
    Small proxy that delays creating AsyncSession until it's actually used.
    API:
      proxy = LazySessionProxy(session_maker=AsyncSessionLocal)
      # anywhere in handlers: session = data['db']; await session.execute(...)
    Implementation detail:
      - session_created flag
      - get_underlying_session() returns actual AsyncSession
      - implements commit(), rollback(), close(), execute(), scalar_one(), etc. by delegating
    """

    def __init__(self, session_maker: Callable[[], AsyncSession]):
        self._maker = session_maker
        self._session: Optional[AsyncSession] = None
        self.session_created = False

    def _ensure(self):
        if not self._session:
            self._session = self._maker()
            self.session_created = True
        return self._session

    def get_underlying_session(self) -> Optional[AsyncSession]:
        return self._session

    # Async helper methods to delegate
    async def execute(self, *args, **kwargs):
        sess = self._ensure()
        return await sess.execute(*args, **kwargs)

    async def commit(self):
        if not self._session:
            return
        return await self._session.commit()

    async def rollback(self):
        if not self._session:
            return
        return await self._session.rollback()

    async def close(self):
        if not self._session:
            return
        try:
            await self._session.close()
        finally:
            self._session = None
            self.session_created = False

    # convenience
    async def scalar_one(self):
        res = await self.execute()
        return res.scalar_one()
