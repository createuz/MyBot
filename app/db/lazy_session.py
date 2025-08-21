# app/db/lazy_session.py
from typing import Optional, Callable, Any, Coroutine

from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession


class LazySessionProxy:
    """
    Lazy AsyncSession proxy for SQLAlchemy.

    - session_maker: callable that returns AsyncSession (e.g. AsyncSessionLocal)
    - session is created only when first DB operation occurs
    - exposes `.info` mapping (like real AsyncSession.info). If session not yet created
      we keep an internal dict and merge into real session.info when created.
    - provides common convenience wrappers: execute(), scalars(stmt), scalar_one(stmt),
      scalar_one_or_none(stmt), commit(), rollback(), close()
    - __getattr__ delegates to underlying session (creating it if needed)
    """

    def __init__(self, session_maker: Callable[[], AsyncSession]):
        self._maker = session_maker
        self._session: Optional[AsyncSession] = None
        self.session_created: bool = False
        # internal info dict used before real session is created
        self._info: dict = {}

    def _ensure(self) -> AsyncSession:
        """
        Ensure underlying AsyncSession exists, create it lazily.
        When real session created, copy any items from _info into session.info.
        """
        if not self._session:
            sess = self._maker()
            # if session maker returns coroutine (unlikely), await it.
            # But async_sessionmaker() returns AsyncSession instance when called.
            if isinstance(sess, Coroutine):
                # This shouldn't normally happen; raise explicit error.
                raise RuntimeError("session_maker returned coroutine, expected AsyncSession instance")
            self._session = sess
            self.session_created = True
            # Merge internal info into session.info (session.info is a dict-like)
            try:
                if hasattr(self._session, "info"):
                    # update session.info with any pre-set flags
                    self._session.info.update(self._info)
                    # point internal info to the real session.info for future sync
                    self._info = self._session.info
            except Exception:
                # be conservative: ignore errors here but keep _info
                pass
        return self._session

    def get_underlying_session(self) -> Optional[AsyncSession]:
        """Return the underlying AsyncSession instance (or None if not created)."""
        return self._session

    # Provide .info property (mapping) similar to AsyncSession.info
    @property
    def info(self) -> dict:
        """
        If underlying session exists, return session.info, else return internal dict.
        Handlers can set db.info['committed_by_handler'] = True safely.
        """
        if self._session:
            try:
                return self._session.info
            except Exception:
                # fallback to internal dict
                return self._info
        return self._info

    # Async delegating methods
    async def execute(self, *args, **kwargs) -> CursorResult:
        sess = self._ensure()
        return await sess.execute(*args, **kwargs)

    async def scalars(self, *args, **kwargs):
        sess = self._ensure()
        res = await sess.execute(*args, **kwargs)
        return res.scalars()

    async def scalar_one(self, statement, *args, **kwargs):
        """Convenience: execute statement and return scalar_one()"""
        sess = self._ensure()
        res = await sess.execute(statement, *args, **kwargs)
        return res.scalar_one()

    async def scalar_one_or_none(self, statement, *args, **kwargs):
        sess = self._ensure()
        res = await sess.execute(statement, *args, **kwargs)
        return res.scalar_one_or_none()

    async def commit(self) -> None:
        if not self._session:
            return
        return await self._session.commit()

    async def rollback(self) -> None:
        if not self._session:
            return
        return await self._session.rollback()

    async def close(self) -> None:
        if not self._session:
            # reset internal info as well
            self._info = {}
            self.session_created = False
            return
        try:
            await self._session.close()
        finally:
            self._session = None
            self.session_created = False
            # keep _info empty after close
            self._info = {}

    # delegate attribute access to underlying session (creates session if needed)
    def __getattr__(self, item: str) -> Any:
        # avoid recursion for our own attributes
        if item.startswith("_"):
            raise AttributeError(item)
        sess = self._ensure()
        return getattr(sess, item)
