# app/db/lazy_session.py
from typing import Optional


class LazySessionProxy:
    """
    Lazily create AsyncSession from an async_sessionmaker when first used.
    Exposes .info dict even before real session exists.
    """

    def __init__(self, session_maker):
        self._SessionMaker = session_maker
        self._session: Optional[object] = None
        self._info = {}

    @property
    def session_created(self) -> bool:
        return self._session is not None

    @property
    def info(self):
        # Return real session.info if created, else the local dict
        if self._session is not None and hasattr(self._session, "info"):
            return self._session.info
        return self._info

    def _ensure_session(self):
        if self._session is None:
            # Create AsyncSession instance
            self._session = self._SessionMaker()
            # transfer info
            try:
                if isinstance(self._info, dict) and hasattr(self._session, "info"):
                    self._session.info.update(self._info)
            except Exception:
                pass

    def __getattr__(self, item):
        # On any attribute access, ensure real session exists and forward
        # note: 'info' will be property accessed before __getattr__
        self._ensure_session()
        return getattr(self._session, item)
