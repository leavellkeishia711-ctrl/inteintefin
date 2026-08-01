"""
Diagnostic script: test INSERT+RETURNING on users table through raw psycopg,
bypassing SQLAlchemy entirely.
Also checks what policies/grants exist.
"""
import asyncio
import uuid
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import psycopg

DSN = "postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require"

async def main():
    # 1. Check policies on users table
    print("=== Step 1: Check RLS policies on users ===")
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT polname, polcmd, pg_get_expr(polqual, polrelid) as using_expr, 
                       pg_get_expr(polwithcheck, polrelid) as check_expr,
                       polroles::regrole[]
                FROM pg_policy WHERE polrelid = 'users'::regclass
            """)
            rows = await cur.fetchall()
            for row in rows:
                print(f"  Policy: {row[0]}, cmd: {row[1]}, USING: {row[2]}, CHECK: {row[3]}, roles: {row[4]}")
            if not rows:
                print("  (no policies found)")
    
    # 2. Check grants
    print("\n=== Step 2: Check grants for app_user on users ===")
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None) as conn:
        async with conn.cursor() as cur:
            for priv in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
                await cur.execute(f"SELECT has_table_privilege('app_user', 'users', '{priv}')")
                result = await cur.fetchone()
                print(f"  {priv}: {result[0]}")
    
    # 3. Try INSERT+RETURNING as app_user via raw psycopg (no SQLAlchemy)
    print("\n=== Step 3: INSERT+RETURNING via raw psycopg as app_user ===")
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with await psycopg.AsyncConnection.connect(DSN, prepare_threshold=None, autocommit=False) as conn:
        async with conn.cursor() as cur:
            # Insert company first (as postgres superuser, before SET ROLE)
            await cur.execute(
                "INSERT INTO companies (id, name, base_currency) VALUES (%s, %s, %s)",
                (str(company_id), "DiagCompany", "USD")
            )
            print("  Company inserted")
            
            # Set tenant context
            await cur.execute("SET LOCAL ROLE app_user")
            await cur.execute("SELECT set_config('app.company_id', %s, true)", (str(company_id),))
            print(f"  Role set to app_user, company_id={company_id}")
            
            # Now try INSERT with RETURNING
            try:
                await cur.execute(
                    """INSERT INTO users (id, company_id, name, email, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING created_at, updated_at""",
                    (str(user_id), str(company_id), "TestUser", "test@diag.com", "hash123", "owner")
                )
                row = await cur.fetchone()
                print(f"  INSERT+RETURNING succeeded! created_at={row[0]}, updated_at={row[1]}")
            except Exception as e:
                print(f"  INSERT+RETURNING FAILED: {type(e).__name__}: {e}")
            
            # Reset role
            try:
                await cur.execute("RESET ROLE")
                print("  RESET ROLE succeeded")
            except Exception as e:
                print(f"  RESET ROLE FAILED: {type(e).__name__}: {e}")
        
        # Try to commit
        try:
            await conn.commit()
            print("  COMMIT succeeded")
        except Exception as e:
            print(f"  COMMIT FAILED: {type(e).__name__}: {e}")
            try:
                await conn.rollback()
                print("  ROLLBACK succeeded after failed commit")
            except Exception as e2:
                print(f"  ROLLBACK also FAILED: {type(e2).__name__}: {e2}")
    
    print("\n=== Step 4: Same test on port 5432 (direct, not Supavisor) ===")
    DSN_DIRECT = "postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require"
    try:
        async with await psycopg.AsyncConnection.connect(DSN_DIRECT, prepare_threshold=None, autocommit=False) as conn:
            async with conn.cursor() as cur:
                company_id2 = uuid.uuid4()
                user_id2 = uuid.uuid4()
                
                await cur.execute(
                    "INSERT INTO companies (id, name, base_currency) VALUES (%s, %s, %s)",
                    (str(company_id2), "DiagCompany2", "USD")
                )
                await cur.execute("SET LOCAL ROLE app_user")
                await cur.execute("SELECT set_config('app.company_id', %s, true)", (str(company_id2),))
                
                await cur.execute(
                    """INSERT INTO users (id, company_id, name, email, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING created_at, updated_at""",
                    (str(user_id2), str(company_id2), "TestUser2", "test2@diag.com", "hash456", "owner")
                )
                row = await cur.fetchone()
                print(f"  Port 5432: INSERT+RETURNING succeeded! created_at={row[0]}")
                
                await cur.execute("RESET ROLE")
            await conn.commit()
            print("  Port 5432: COMMIT succeeded")
    except Exception as e:
        print(f"  Port 5432: FAILED: {type(e).__name__}: {e}")
    
    print("\nDone.")

if __name__ == "__main__":
    asyncio.run(main())
