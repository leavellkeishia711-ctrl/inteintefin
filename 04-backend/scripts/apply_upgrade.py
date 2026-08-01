import psycopg2
import time
import sys

try:
    with open('upgrade.sql', 'r', encoding='utf-16le') as f:
        sql = f.read().lstrip('\ufeff')

    statements = [s.strip() for s in sql.split(';') if s.strip()]
    
    for s in statements:
        success = False
        attempts = 0
        while not success and attempts < 5:
            try:
                c = psycopg2.connect('postgresql://postgres.dkgkilpqaigmviyhfmuh:Ebriksas123!@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require', connect_timeout=10)
                c.autocommit = True
                cur = c.cursor()
                print("Executing:", s[:50].replace('\n', ' '), "...")
                cur.execute(s)
                c.close()
                success = True
                time.sleep(0.5)
            except Exception as e:
                err = str(e)
                if "already exists" in err or "already a policy" in err or "relation \"alembic_version\" already exists" in err:
                    print("Skipping (already exists/applied)")
                    success = True
                else:
                    print(f"Statement failed (attempt {attempts+1}): {err.strip()}")
                    attempts += 1
                    time.sleep(2)
        if not success:
            print("Failed completely.")
            sys.exit(1)

    print("Upgrade applied successfully!")
except Exception as e:
    print(f"Fatal Error: {e}")
    sys.exit(1)
