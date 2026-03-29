"""FastAPI dependencies — DB session, pagination."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from snep.db import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


class Pagination:
    def __init__(
        self,
        offset: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(50, ge=1, le=500, description="Max items to return"),
    ):
        self.offset = offset
        self.limit = limit


PaginationDep = Annotated[Pagination, Depends()]
