import base64
import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Создаёт таблицы и декодирует credentials.json если нужно."""
    # Декодируем credentials.json из base64 (для Railway)
    creds_b64 = settings.google_credentials_base64
    if creds_b64:
        creds_path = settings.google_sheets_key_file
        with open(creds_path, "wb") as f:
            f.write(base64.b64decode(creds_b64))

    from shared.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ БД готова.")
