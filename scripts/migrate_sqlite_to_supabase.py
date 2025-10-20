"""Simple migration helper: copy data from local sqlite DB to a Postgres DB (Supabase)

Usage:
  - Set environment variable DATABASE_URL to your Supabase Postgres connection string (pg URI)
  - Ensure local sqlite path matches the app (database/app.db)
  - Run: python scripts/migrate_sqlite_to_supabase.py

Notes:
  - This script performs a best-effort field mapping for `user` and `note` tables defined in the project.
  - It's safe to run on an empty target DB. If tables already exist, duplicates may be created.
  - For large datasets or production, prefer more robust tooling (pgloader, logical replication, pg_dump/pg_restore).
"""
import os
from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SQLITE_PATH = os.path.join(ROOT, 'database', 'app.db')
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"

SUPABASE_URL = os.environ.get('DATABASE_URL')
if not SUPABASE_URL:
    raise SystemExit('DATABASE_URL not set. Set it to your Supabase Postgres URL and re-run.')

print('Local sqlite:', SQLITE_URL)
print('Target Postgres (Supabase):', SUPABASE_URL)

# create engines
src_engine = create_engine(SQLITE_URL)
dst_engine = create_engine(SUPABASE_URL)

src_meta = MetaData(bind=src_engine)
dst_meta = MetaData(bind=dst_engine)

src_meta.reflect(only=['user', 'note'])
dst_meta.reflect()

SessionDst = sessionmaker(bind=dst_engine)

def copy_table(table_name, pk='id'):
    src_table = Table(table_name, src_meta, autoload_with=src_engine)
    # ensure target has table
    if table_name not in dst_meta.tables:
        print(f"Target DB missing table '{table_name}'. Create it first (run alembic migrations). Skipping.")
        return 0
    dst_table = Table(table_name, dst_meta, autoload_with=dst_engine)

    conn_src = src_engine.connect()
    conn_dst = dst_engine.connect()
    trans = conn_dst.begin()
    try:
        rows = list(conn_src.execute(select(src_table)))
        count = 0
        for r in rows:
            data = dict(r)
            # remove primary key to let Postgres assign if serial differs
            if pk in data:
                data.pop(pk, None)
            conn_dst.execute(dst_table.insert().values(**data))
            count += 1
        trans.commit()
        print(f'Copied {count} rows into {table_name}')
        return count
    except SQLAlchemyError as e:
        trans.rollback()
        print('Error copying', table_name, e)
        return 0
    finally:
        conn_src.close()
        conn_dst.close()

if __name__ == '__main__':
    copied_users = copy_table('user')
    copied_notes = copy_table('note')
    print('Done. Users:', copied_users, 'Notes:', copied_notes)
