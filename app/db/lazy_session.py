# app/db/lazy_session.py
from typing import Optional, Callable

from sqlalchemy.ext.asyncio import AsyncSession


class LazySessionProxy:
    """
    Delayed AsyncSession creator. Creates AsyncSession only when first used.
    Exposes `.info` property so handlers can set flags (like committed_by_handler).
    """

    def __init__(self, session_maker: Callable[..., AsyncSession]):
        self._maker = session_maker
        self._session: Optional[AsyncSession] = None
        self.session_created: bool = False

    def _ensure(self) -> AsyncSession:
        if not self._session:
            # session_maker is a factory (async_sessionmaker) which returns AsyncSession
            self._session = self._maker()
            self.session_created = True
        return self._session

    def get_underlying_session(self) -> Optional[AsyncSession]:
        return self._session

    # expose info dict (this will create session on first access)
    @property
    def info(self) -> dict:
        sess = self._ensure()
        return sess.info

    # delegate key async methods
    async def execute(self, *args, **kwargs):
        sess = self._ensure()
        return await sess.execute(*args, **kwargs)

    async def scalar_one_or_none(self, *args, **kwargs):
        sess = self._ensure()
        res = await sess.execute(*args, **kwargs)
        return res.scalars().first()

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
