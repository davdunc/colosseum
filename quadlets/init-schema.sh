#!/bin/bash
# Initialize Colosseum database schema
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🏛️  Initializing Colosseum Database Schema"
echo "==========================================="

# Check if container is running
if ! podman ps --format "{{.Names}}" | grep -q "^colosseum-postgres$"; then
    echo "❌ Error: colosseum-postgres container is not running"
    echo "   Run ./deploy.sh first"
    exit 1
fi

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if podman exec colosseum-postgres pg_isready -U colosseum -d colosseum_data_lake &>/dev/null; then
        echo "   ✅ PostgreSQL is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL did not become ready in time"
        exit 1
    fi
    sleep 2
done

# Run the initialization SQL
echo "📝 Running database initialization script..."
if podman exec -i colosseum-postgres psql -U colosseum -d colosseum_data_lake < "${SCRIPT_DIR}/init-db.sql"; then
    echo "✅ Database schema initialized successfully!"
else
    echo "❌ Failed to initialize database schema"
    exit 1
fi

# Show some statistics
echo ""
echo "📊 Database Information:"
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c "
SELECT
    schemaname,
    COUNT(*) as table_count
FROM pg_tables
WHERE schemaname IN ('market_data', 'agent_data', 'metadata')
GROUP BY schemaname
ORDER BY schemaname;
"

echo ""
echo "🔌 Extensions:"
podman exec colosseum-postgres psql -U colosseum -d colosseum_data_lake -c "
SELECT extname, extversion FROM pg_extension WHERE extname IN ('pgvector', 'timescaledb');
"

echo ""
echo "✅ Initialization complete!"
echo ""
echo "💡 Connect to the database:"
echo "   podman exec -it colosseum-postgres psql -U colosseum -d colosseum_data_lake"
