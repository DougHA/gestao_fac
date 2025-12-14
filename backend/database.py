import os
from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

# Carrega as variáveis do arquivo .env
load_dotenv()

# Recupera a URL ou usa um valor default (útil para debug)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("A variável de ambiente DATABASE_URL não está definida!")

# Criação do Engine para PostgreSQL
# Nota: Removemos 'check_same_thread' pois o Postgres lida nativamente com concorrência
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Mantém logs de SQL visíveis para debug
    future=True
)

async def init_db():
    """
    Cria as tabelas no PostgreSQL na inicialização.
    O SQLModel traduzirá os modelos Python para tabelas SQL compatíveis com Postgres.
    """
    async with engine.begin() as conn:
        # Cria as tabelas se não existirem
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    """Injeção de dependência para rotas FastAPI"""
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session