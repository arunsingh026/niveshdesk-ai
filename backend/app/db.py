from sqlalchemy import create_engine,event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, with_loader_criteria
from .config import settings
engine = create_engine(settings.database_url, pool_pre_ping=True)
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
