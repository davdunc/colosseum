#!/bin/bash
# Deploy Colosseum to Kubernetes
set -euo pipefail

NAMESPACE="${NAMESPACE:-colosseum}"
CONTEXT="${CONTEXT:-kind-colosseum}"

echo "🏛️  Deploying Colosseum to Kubernetes"
echo "======================================"
echo "Namespace: $NAMESPACE"
echo "Context:   $CONTEXT"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

# Check if context exists
if ! kubectl config get-contexts "$CONTEXT" &> /dev/null; then
    echo "⚠️  Context '$CONTEXT' not found."
    echo "   Available contexts:"
    kubectl config get-contexts
    echo ""
    read -p "Continue with current context? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        exit 0
    fi
else
    kubectl config use-context "$CONTEXT"
fi

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f namespace.yaml

# Create secrets
echo "🔐 Creating secrets..."
if kubectl get secret postgres-credentials -n "$NAMESPACE" &> /dev/null; then
    echo "   Secret 'postgres-credentials' already exists"
else
    echo -n "   Generating PostgreSQL password... "
    DB_PASSWORD=$(openssl rand -base64 32)
    kubectl create secret generic postgres-credentials \
        --from-literal=password="$DB_PASSWORD" \
        -n "$NAMESPACE"
    echo "✅"
    echo "   💾 Save this password: $DB_PASSWORD"
fi

# Deploy PostgreSQL
echo "🗄️  Deploying PostgreSQL..."
kubectl apply -f postgres-statefulset.yaml

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n "$NAMESPACE" --timeout=300s

# Initialize database schema
echo "📝 Initializing database schema..."
kubectl cp ../../quadlets/init-db.sql "$NAMESPACE/postgres-0:/tmp/init-db.sql"
kubectl exec -n "$NAMESPACE" postgres-0 -- \
    psql -U colosseum -d colosseum_data_lake -f /tmp/init-db.sql

# Deploy ConfigMaps
echo "⚙️  Deploying ConfigMaps..."
kubectl apply -f curator-deployment.yaml

# Deploy Curator
echo "🏛️  Deploying CuratorAgent..."
kubectl apply -f curator-deployment.yaml

# Wait for Curator to be ready
echo "⏳ Waiting for Curator to be ready..."
kubectl wait --for=condition=available deployment/curator -n "$NAMESPACE" --timeout=300s

# Show status
echo ""
echo "📊 Deployment Status:"
kubectl get all -n "$NAMESPACE"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Useful commands:"
echo "   Status:   kubectl get all -n $NAMESPACE"
echo "   Logs:     kubectl logs -f deployment/curator -n $NAMESPACE"
echo "   Shell:    kubectl exec -it deployment/curator -n $NAMESPACE -- bash"
echo "   DB:       kubectl exec -it postgres-0 -n $NAMESPACE -- psql -U colosseum -d colosseum_data_lake"
echo "   Describe: kubectl describe pod -l app=curator -n $NAMESPACE"
echo ""
echo "🔍 Check curator health:"
echo "   kubectl exec deployment/curator -n $NAMESPACE -- python -m colosseum.cli.curator health"
