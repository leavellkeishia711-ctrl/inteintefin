# DevOps & Deployment

## Supabase Database Setup
When deploying to Supabase (or any PostgreSQL instance), some extensions require superuser privileges to create. 

### Required Extensions
Before running the first Alembic migration, you MUST manually enable the `btree_gist` and `citext` extensions via the Supabase SQL Editor. 
The migration script has a safety check and will not fail destructively, but the extensions are necessary for constraints to work correctly.

Run the following in the Supabase SQL Editor:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA extensions;
```

### Migrations
Always run migrations via the Direct URL (Port 5432 or standard session mode). Do NOT run migrations via the Transaction Pooler (Port 6543) as Supabase's transaction mode doesn't support features required by Alembic or SQLAlchemy during schema migrations.

```bash
alembic upgrade head
```
