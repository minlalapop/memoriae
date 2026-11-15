import hashlib
from datetime import timedelta

import pytest
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.database import Base, build_engine, get_session
from app.main import app
from app.persistence.database import utc_now
from app.persistence.models import ResearcherSession


def _test_client(db_session, *, authenticated: bool):
    def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    test_client = TestClient(app)
    if authenticated:
        token = "test-researcher-session"
        db_session.add(
            ResearcherSession(
                username="chercheur-test",
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                expires_at=utc_now() + timedelta(hours=1),
            )
        )
        db_session.commit()
        test_client.cookies.set("memoriae_researcher", token)
    return test_client


@pytest.fixture
def db_session(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}", echo=False)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session):
    test_client = _test_client(db_session, authenticated=True)
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()


@pytest.fixture
def anonymous_client(db_session):
    test_client = _test_client(db_session, authenticated=False)
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()

