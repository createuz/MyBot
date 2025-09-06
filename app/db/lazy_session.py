# app/db/lazy_session.py

from typing import Optional, Callable, Any, cast

from sqlalchemy.ext.asyncio import AsyncSession


class LazySessionProxy:
    def __init__(self, session_maker: Callable[..., AsyncSession]):
        self._maker = session_maker
        self._session: Optional[AsyncSession] = None
        self.session_created: bool = False

    def _ensure(self) -> AsyncSession:
        if not self._session:
            self._session = self._maker()
            self.session_created = True
            if not hasattr(self._session, "info"):
                try:
                    setattr(self._session, "info", {})
                except Exception:
                    pass
            else:
                _ = cast(Any, self._session).info
        return self._session

    def get_underlying_session(self) -> Optional[AsyncSession]:
        return self._session

    @property
    def info(self) -> dict:
        return self._ensure().info

    async def execute(self, *args, **kwargs):
        return await self._ensure().execute(*args, **kwargs)

    async def scalar_one(self, *args, **kwargs):
        res = await self.execute(*args, **kwargs)
        return res.scalar_one()

    async def scalar_one_or_none(self, *args, **kwargs):
        res = await self.execute(*args, **kwargs)
        return res.scalars().first()

    async def commit(self):
        if not self._session:
            return None
        return await self._session.commit()

    async def rollback(self):
        if not self._session:
            return None
        return await self._session.rollback()

    async def close(self):
        if not self._session:
            return
        try:
            await self._session.close()
        finally:
            self._session = None
            self.session_created = False
