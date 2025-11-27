# Kubernetes Развертывание

## Обзор

Kubernetes развертывание подходит для высоконагруженных систем с требованиями к высокой доступности и автомасштабированию.

## Требования

- Kubernetes 1.24+
- kubectl настроен
- Helm 3+ (опционально)
- Ingress Controller (nginx/traefik)
- Cert-Manager для SSL

## Структура манифестов

```
infrastructure/kubernetes/
├── namespace.yaml
├── configmap.yaml
├── secrets.yaml
├── postgres/
│   ├── statefulset.yaml
│   ├── service.yaml
│   └── pvc.yaml
├── redis/
│   ├── deployment.yaml
│   └── service.yaml
├── bot/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   └── ingress.yaml
└── monitoring/
    ├── prometheus.yaml
    └── grafana.yaml
```

## Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: 2getpro-v2
  labels:
    name: 2getpro-v2
```

## ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: bot-config
  namespace: 2getpro-v2
data:
  POSTGRES_HOST: "postgres-service"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "2getpro_v2"
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  WEB_SERVER_HOST: "0.0.0.0"
  WEB_SERVER_PORT: "8080"
  PROMETHEUS_PORT: "9090"
```

## Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: bot-secrets
  namespace: 2getpro-v2
type: Opaque
stringData:
  BOT_TOKEN: "your_bot_token"
  POSTGRES_PASSWORD: "your_db_password"
  REDIS_PASSWORD: "your_redis_password"
  YOOKASSA_SECRET_KEY: "your_yookassa_key"
  PANEL_API_KEY: "your_panel_key"
```

Создание из файла:

```bash
kubectl create secret generic bot-secrets \
  --from-env-file=.env \
  --namespace=2getpro-v2
```

## PostgreSQL

```yaml
# postgres/statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: 2getpro-v2
spec:
  serviceName: postgres-service
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: bot-config
              key: POSTGRES_DB
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: 2getpro-v2
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None
```

## Redis

```yaml
# redis/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: 2getpro-v2
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command: ["redis-server"]
        args: ["--requirepass", "$(REDIS_PASSWORD)"]
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: bot-secrets
              key: REDIS_PASSWORD
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: 2getpro-v2
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

## Bot Deployment

```yaml
# bot/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bot
  namespace: 2getpro-v2
spec:
  replicas: 2
  selector:
    matchLabels:
      app: bot
  template:
    metadata:
      labels:
        app: bot
    spec:
      containers:
      - name: bot
        image: your-registry/2getpro-v2:latest
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: bot-config
        - secretRef:
            name: bot-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: bot-service
  namespace: 2getpro-v2
spec:
  selector:
    app: bot
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 9090
    targetPort: 9090
  type: ClusterIP
```

## Horizontal Pod Autoscaler

```yaml
# bot/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: bot-hpa
  namespace: 2getpro-v2
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: bot
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Ingress

```yaml
# bot/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: bot-ingress
  namespace: 2getpro-v2
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - your-domain.com
    secretName: bot-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: bot-service
            port:
              number: 80
```

## Развертывание

```bash
# Создание namespace
kubectl apply -f namespace.yaml

# Создание secrets
kubectl apply -f secrets.yaml

# Создание configmap
kubectl apply -f configmap.yaml

# Развертывание PostgreSQL
kubectl apply -f postgres/

# Развертывание Redis
kubectl apply -f redis/

# Развертывание Bot
kubectl apply -f bot/

# Проверка статуса
kubectl get pods -n 2getpro-v2
kubectl get svc -n 2getpro-v2
```

## Мониторинг

```bash
# Логи
kubectl logs -f deployment/bot -n 2getpro-v2

# Метрики
kubectl top pods -n 2getpro-v2

# События
kubectl get events -n 2getpro-v2

# Описание pod
kubectl describe pod <pod-name> -n 2getpro-v2
```

## Обновление

### Rolling Update

```bash
# Обновление образа
kubectl set image deployment/bot bot=your-registry/2getpro-v2:v2.0.0 -n 2getpro-v2

# Проверка статуса
kubectl rollout status deployment/bot -n 2getpro-v2

# История
kubectl rollout history deployment/bot -n 2getpro-v2
```

### Откат

```bash
# Откат к предыдущей версии
kubectl rollout undo deployment/bot -n 2getpro-v2

# Откат к конкретной ревизии
kubectl rollout undo deployment/bot --to-revision=2 -n 2getpro-v2
```

## Резервное копирование

```yaml
# backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: 2getpro-v2
spec:
  schedule: "0 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres-service -U postgres 2getpro_v2 | gzip > /backup/db_$(date +%Y%m%d_%H%M%S).sql.gz
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: bot-secrets
                  key: POSTGRES_PASSWORD
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

## Дополнительные ресурсы

- [Deployment Overview](./README.md)
- [Docker Deployment](./docker.md)
- [Production Checklist](./production.md)