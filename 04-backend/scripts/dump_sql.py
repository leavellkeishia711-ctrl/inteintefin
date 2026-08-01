from app.db.models import Base
from sqlalchemy import create_mock_engine
from sqlalchemy.dialects import postgresql

def dump(sql, *m, **p):
    print(sql.compile(dialect=postgresql.dialect()), ";")

e = create_mock_engine('postgresql://', dump)
Base.metadata.create_all(e, checkfirst=False)
