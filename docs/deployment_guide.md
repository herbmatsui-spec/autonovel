# Deployment Guide for Novel Generation System

This document describes the production deployment of the novel generation system, covering Docker-based deployment, Kubernetes manifests, and operational runbooks.

## Table of Contents
1. [System Overview](#system-overview)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Configuration Management](#configuration-management)
5. [Environment Variables](#environment-variables)
6. [Health Checks & Monitoring](#health-checks--monitoring)
7. [Backup & Recovery](#backup--recovery)
8. [Rollback Strategy](#rollback-strategy)
9. [Performance Benchmarking](#performance-benchmarking)
10. [Operational Runbooks](#operational-runbooks)
11. [API Endpoint Reference](#api-endpoint-reference)
12. [Appendix: Sample Configurations](#appendix-sample-configurations)

---

## System Overview
The system consists of three primary components:
- **Backend (FastAPI)**: Provides RESTful APIs for novel production, status tracking, and report generation.
- **Frontend (Streamlit)**: User interface for configuring novel settings, triggering commercial pipelines, and downloading artifacts.
- **Support Services**: Redis (task queue), optional vector stores for RAG, and Prometheus (metrics).

All services are containerized and orchestrated via Docker Compose in development and Kubernetes in production.

---

## Docker Deployment

### Prerequisites
- Docker Engine >= 20.10
- Docker Compose >= 2.0
- Access to the Git repository containing the source code

### Build & Run
```bash
# Clone the repository
git clone <repo-url>
cd <repo-directory>

# Build all images and start containers
docker-compose up --build -d

# Verify services
docker-compose ps
```

### Stopping the Stack
```bash
docker-compose down
```

### Volume Persistence
- **Redis data**: Persisted via a named volume `redis_data`.
- **Generated artifacts**: The `/output` directory is mapped to a host volume `./artifacts` for easy access.

### Production Flags
When running in production, add the following to `docker-compose.yml`:
- `--no-deps` to avoid rebuilding dependent services unnecessarily.
- `--restart unless-stopped` to ensure containers restart automatically.

---

## Kubernetes Deployment

### Namespace
Create a dedicated namespace for isolation:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: novel-system
```

### Deployment Manifests
Place the following manifests under `k8s/` directory.

#### 1. Backend Deployment (`k8s/backend-deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: novel-backend
  namespace: novel-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: novel-backend
  template:
    metadata:
      labels:
        app: novel-backend
    spec:
      containers:
        - name: backend
          image: your-registry/novel-backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: novel-config
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 60
          resources:
            limits:
              cpu: "500m"
              memory: "512Mi"
            requests:
              cpu: "250m"
              memory: "256Mi"
```

#### 2. Frontend Deployment (`k8s/frontend-deployment.yaml`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: novel-frontend
  namespace: novel-system
spec:
  replicas: 2
  selector:
    matchLabels:
      app: novel-frontend
  template:
    metadata:
      labels:
        app: novel-frontend
    spec:
      containers:
        - name: frontend
          image: your-registry/novel-frontend:latest
          ports:
            - containerPort: 8501
          envFrom:
            - configMapRef:
                name: novel-config
          readinessProbe:
            httpGet:
              path: /
              port: 8501
            initialDelaySeconds: 5
            periodSeconds: 15
          livenessProbe:
            httpGet:
              path: /
              port: 8501
            initialDelaySeconds: 10
            periodSeconds: 30
          resources:
            limits:
              cpu: "400m"
              memory: "256Mi"
            requests:
              cpu: "200m"
              memory: "128Mi"
```

#### 3. Service Definitions (`k8s/services.yaml`)
```yaml
apiVersion: v1
kind: Service
metadata:
  name: novel-backend-svc
  namespace: novel-system
spec:
  selector:
    app: novel-backend
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: novel-frontend-svc
  namespace: novel-system
spec:
  selector:
    app: novel-frontend
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8501
  type: LoadBalancer   # Use NodePort or Ingress depending on cluster
```

#### 4. Ingress (Optional)
If an ingress controller is available (e.g., NGINX, ALB), expose the frontend via:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: novel-ingress
  namespace: novel-system
spec:
  rules:
    - host: novel.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: novel-frontend-svc
                port:
                  number: 80
```

### Applying the Manifests
```bash
# Apply namespace
kubectl apply -f k8s/namespace.yaml

# Apply backend and frontend deployments
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

# Apply services
kubectl apply -f k8s/services.yaml

# (Optional) Apply ingress
kubectl apply -f k8s/ingress.yaml
```

### Service Discovery
- **Backend**: Accessible at `http://novel-backend-svc.novel-system.svc.cluster.local/api/...`
- **Frontend**: Accessible via the external LoadBalancer IP orIngress hostname.

---

## Configuration Management

### ConfigMap
All environment-specific configurations are centralized in a ConfigMap named `novel-config`. Example:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: novel-config
  namespace: novel-system
data:
  API_KEY: "prod-secret-key"
  DATABASE_URL: "postgresql://user:pass@db/novel_db"
  REDIS_URL: "redis://redis:6379/0"
  LOG_LEVEL: "INFO"
```

Apply with:
```bash
kubectl apply -f k8s/configmap.yaml
```

Update the ConfigMap and roll the deployments to pick up changes:
```bash
kubectl rollout restart deployment/novel-backend -n novel-system
kubectl rollout restart deployment/novel-frontend -n novel-system
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Authentication token for internal services | `None` |
| `DATABASE_URL` | PostgreSQL connection string | `None` |
| `REDIS_URL` | Redis endpoint for Celery/RQ | `redis://redis:6379/0` |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |
| `TOKEN_EXPIRY_MINUTES` | Token validity period | `1440` |

These can be overridden per environment (dev / staging / prod).

---

## Health Checks & Monitoring

- **Backend `/health`**: Returns 200 OK when the service is ready.
- **Metrics**: Exported via `/metrics` (Prometheus format) when `ENABLE_METRICS=true`.
- **Alerting**: Configure Prometheus alerts for high error rates or latency.

---

## Backup & Recovery

1. **Redis Persistence**: The Redis data volume (`redis_data`) is snapshot-backed by the underlying storage.
2. **Artifact Storage**: All generated novels and reports are stored under the persistent volume `./artifacts`. Back up this directory regularly.
3. **Database**: Periodic dumps of the PostgreSQL database should be scheduled via `cron` jobs or managed backup services.

---

## Rollback Strategy

- **Docker**: `docker-compose down` removes containers; use `docker-compose pull` followed by `docker-compose up` to redeploy the previous known-good image tags.
- **Kubernetes**: Use `kubectl rollout undo deployment/novel-backend -n novel-system` to revert to the previous revision.

---

## Performance Benchmarking

- **Load Testing**: Use `Locust` or `k6` to simulate realistic user loads against the `/api/commercial/run` endpoint.
- **Metrics to Capture**:
  - Requests per second (RPS)
  - Latency (p50, p95, p99)
  - Error rate
- **Resource Scaling**: Adjust replica counts based on observed CPU/ Memory usage.

---

## Operational Runbooks

### 1. Deploy a New Version
```bash
# 1. Build and push the new image
docker build -t your-registry/novel-backend:1.2.3 ./src/backend
docker push your-registry/novel-backend:1.2.3

# 2. Update the Deployment image
kubectl set image deployment/novel-backend -n novel-system novel-backend=your-registry/novel-backend:1.2.3

# 3. Wait for rollout completion
kubectl rollout status deployment/novel-backend -n novel-system

# 4. Repeat for frontend if needed
```

### 2. Emergency Restart
If the backend becomes unresponsive:
```bash
kubectl delete pod -n novel-system -l app=novel-backend
```
Kubernetes will automatically recreate the pod.

### 3. View Logs
```bash
kubectl logs -f pod -n novel-system -l app=novel-backend
```

### 4. Database Maintenance
```sql
-- Example: Vacuum PostgreSQL tables
VACUUM ANALYZE novel_production;
```

---

## API Endpoint Reference

| Method | Endpoint | Description | Request Body (JSON) | Response |
|--------|----------|-------------|---------------------|----------|
| `POST` | `/api/commercial/run` | Execute the commercial pipeline | `CommercialConfig` | `CommercialPipelineResult` |
| `GET` | `/api/tasks/{task_id}/status` | Retrieve task status | – | `{status, progress, message}` |
| `GET` | `/api/novel/{project_id}/episodes` | List episodes | – | `EpisodeListResponse` |
| `GET` | `/api/novel/{project_id}/report` | Download production report | – | `ProductionReport` |
| `GET` | `/health` | Health check | – | `HealthStatus` |

Refer to `src/models/api_schemas.py` for full request/response models.

---

## Appendix: Sample Configurations

### `docker-compose.yml` (Development)
```yaml
version: "3.9"
services:
  backend:
    build: ./src/backend
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./src/backend:/app
    depends_on:
      - redis
  frontend:
    build: ./streamlit_app
    ports:
      - "8501:8501"
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./streamlit_app:/app
    depends_on:
      - backend
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### `k8s/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: novel-system
```

(Other manifests are referenced in the text above.)

---

**End of Document**