from sqlalchemy import create_engine,event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, with_loader_criteria
from .config import settings


def normalize_database_url(url: str) -> str:
    """Use the installed Psycopg 3 driver for provider-issued Postgres URLs."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


database_url = normalize_database_url(settings.database_url)
engine_options = {"pool_pre_ping": True}
if database_url.startswith("postgresql+psycopg://"):
    engine_options.update(
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=300,
    )
    if settings.database_ssl_mode:
        engine_options["connect_args"] = {"sslmode": settings.database_ssl_mode}

engine = create_engine(database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass

@event.listens_for(Session,"do_orm_execute")
def scope_user_queries(execute_state):
    user_id=execute_state.session.info.get("user_id")
    if not user_id or not execute_state.is_select:
        return
    statement=execute_state.statement
    for mapper in tuple(Base.registry.mappers):
        model=mapper.class_
        if getattr(model,"__user_owned__",False):
            statement=statement.options(with_loader_criteria(model,model.user_id==user_id,include_aliases=True))
    execute_state.statement=statement

@event.listens_for(Session,"before_flush")
def assign_user_ownership(session,flush_context,instances):
    user_id=session.info.get("user_id")
    if not user_id:
        return
    for item in session.new:
        if getattr(item,"__user_owned__",False) and item.user_id is None:
            item.user_id=user_id

def init_db():
    from . import models
    Base.metadata.create_all(bind=engine)
    from .migrations import migrate_user_ownership
    migrate_user_ownership(engine)
