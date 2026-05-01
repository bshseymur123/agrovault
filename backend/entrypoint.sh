#!/bin/bash
set -e

echo "🌱 AgroVault Backend starting..."

# Run DB migrations / table creation
python -c "
from db.session import Base, engine
from models.models import *
Base.metadata.create_all(bind=engine)
print('✓ Database tables ready')
"

# Seed only if users table is empty
python -c "
from db.session import SessionLocal
from models.models import User
db = SessionLocal()
count = db.query(User).count()
db.close()
if count == 0:
    import subprocess
    result = subprocess.run(['python', 'seed.py'], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print('Seed error:', result.stderr)
else:
    print(f'✓ Database already has {count} users — skipping seed')
"

echo "🚀 Starting uvicorn on port 8000..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 --log-level info
