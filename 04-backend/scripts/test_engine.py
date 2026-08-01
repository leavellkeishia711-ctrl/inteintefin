from sqlalchemy import create_engine
from sqlalchemy import text
from app.core.config import settings

url = str(settings.DATABASE_URL).replace("asyncpg", "psycopg2").replace(":5432", ":6543").replace("?sslmode=require", "").replace("&sslmode=require", "")

engine = create_engine(
    url,
    echo=True,
)

with engine.connect() as conn:
    print("Connected!")
    res = conn.execute(text("SELECT 1"))
    print(res.scalar())
