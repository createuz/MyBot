# app/db/lazy_session.py
from typing import Optional, Callable, Any, Coroutine

from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession


class LazySessionProxy:
    """
    Lazy AsyncSession proxy:
      - session_maker: callable -> AsyncSession (async_sessionmaker)
      - creates session lazily on first DB call
      - exposes .info dict even before session created
      - session_created flag + get_underlying_session()
      - common delegations: execute, scalars, scalar_one, commit, rollback, close
    """

    def __init__(self, session_maker: Callable[[], AsyncSession]):
        self._maker = session_maker
        self._session: Optional[AsyncSession] = None
        self.session_created: bool = False
        self._info = {}  # local info until real session exists

    def _ensure(self) -> AsyncSession:
        if not self._session:
            sess = self._maker()
            # async_sessionmaker returns AsyncSession instance when called
            if isinstance(sess, Coroutine):
                # shouldn't happen with async_sessionmaker; fail loudly
                raise RuntimeError("session_maker returned coroutine, expected AsyncSession instance")
            self._session = sess
            self.session_created = True
            # merge pre-set info into session.info if possible
            try:
                if hasattr(self._session, "info"):
                    # copy keys
                    self._session.info.update(self._info)
                    self._info = self._session.info
            except Exception:
                pass
        return self._session

    def get_underlying_session(self) -> Optional[AsyncSession]:
        return self._session

    @property
    def info(self) -> dict:
        if self._session:
            try:
                return self._session.info
            except Exception:
                return self._info
        return self._info

    # Delegations for async usage
    async def execute(self, *args, **kwargs) -> CursorResult:
        sess = self._ensure()
        return await sess.execute(*args, **kwargs)

    async def scalars(self, *args, **kwargs):
        sess = self._ensure()
        res = await sess.execute(*args, **kwargs)
        return res.scalars()

    async def scalar_one(self, statement, *args, **kwargs):
        sess = self._ensure()
        res = await sess.execute(statement, *args, **kwargs)
        return res.scalar_one()

    async def scalar_one_or_none(self, statement, *args, **kwargs):
        sess = self._ensure()
        res = await sess.execute(statement, *args, **kwargs)
        return res.scalar_one_or_none()

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
            self._info = {}
            self.session_created = False
            return
        try:
            await self._session.close()
        finally:
            self._session = None
            self.session_created = False
            self._info = {}

    def __getattr__(self, item: str) -> Any:
        if item.startswith("_"):
            raise AttributeError(item)
        sess = self._ensure()
        return getattr(sess, item)
