# Infrastructure Configuration для 2GETPRO v2

Этот каталог содержит все необходимые конфигурационные файлы для production развертывания бота 2GETPRO v2.

## 📁 Структура

```
infrastructure/
├── kubernetes/          # Kubernetes манифесты
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   └── pvc.yaml
├── nginx/              # Nginx конфигурации
│   ├── nginx.conf
│   └── webhook.conf
├── prometheus/         # Prometheus конфигурации
│   ├── prometheus.yml
│   └── alerts/
│       ├── bot_alerts.yml
│       ├── infrastructure_alerts.yml
│       └── database_alerts.yml
├── grafana/           # Grafana конфигурации
│   ├── provisioning/
│   │   └── datasources.yml
│   └── dashboards/
│       └── README.md
├── docker/            # Docker Compose для продакшн
│   └── docker-compose.prod.yml
├── systemd/           # Systemd service файлы
│   ├── 2getpro-v2.service
│   └── scripts/
│       ├── pre-start.sh
│       └── graceful-stop.sh
└── README.md          # Этот файл
```

## 🚀 Варианты развертывания

### 1. Kubernetes (Рекомендуется для продакшн)

#### Предварительные требования:
- Kubernetes кластер (версия 1.24+)
- kubectl настроен и подключен к кластеру
- Helm 3 (опционально)
- cert-manager для SSL сертификатов

#### Шаги развертывания:

**1. Создайте namespace:**
```bash
kubectl apply -f kubernetes/namespace.yaml
```

**2. Настройте secrets:**
```bash
# Отредактируйте secrets.yaml и замените все значения на реальные
vim kubernetes/secrets.yaml

# Или создайте secrets через kubectl
kubectl create secret generic 2getpro-v2-secrets \
  --from-literal=BOT_TOKEN=your_bot_token \
  --from-literal=DB_PASSWORD=your_db_password \
  --from-literal=REDIS_PASSWORD=your_redis_password \
  -n 2getpro-v2

# Примените secrets
kubectl apply -f kubernetes/secrets.yaml
```

**3. Примените ConfigMap:**
```bash
kubectl apply -f kubernetes/configmap.yaml
```

**4. Создайте PersistentVolumeClaims:**
```bash
kubectl apply -f kubernetes/pvc.yaml
```

**5. Разверните базу данных и Redis:**
```bash
kubectl apply -f kubernetes/deployment.yaml
```

**6. Создайте Services:**
```bash
kubectl apply -f kubernetes/service.yaml
```

**7. Настройте Ingress:**
```bash
# Отредактируйте ingress.yaml и укажите ваш домен
vim kubernetes/ingress.yaml

kubectl apply -f kubernetes/ingress.yaml
```

**8. Настройте HPA:**
```bash
kubectl apply -f kubernetes/hpa.yaml
```

**9. Проверьте статус:**
```bash
# Проверка подов
kubectl get pods -n 2getpro-v2

# Проверка сервисов
kubectl get svc -n 2getpro-v2

# Проверка ingress
kubectl get ingress -n 2getpro-v2

# Логи бота
kubectl logs -f deployment/2getpro-v2-bot -n 2getpro-v2
```

#### Обновление:
```bash
# Обновление образа
kubectl set image deployment/2getpro-v2-bot bot=2getpro-v2:new-version -n 2getpro-v2

# Откат к предыдущей версии
kubectl rollout undo deployment/2getpro-v2-bot -n 2getpro-v2

# История развертываний
kubectl rollout history deployment/2getpro-v2-bot -n 2getpro-v2
```

---

### 2. Docker Compose (Для небольших развертываний)

#### Предварительные требования:
- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 20GB+ свободного места на диске

#### Шаги развертывания:

**1. Подготовьте окружение:**
```bash
# Создайте директории для данных
sudo mkdir -p /var/lib/2getpro/{postgres,redis,prometheus,grafana}
sudo mkdir -p /var/backups/2getpro/postgres
sudo mkdir -p /var/log/{2getpro,nginx}

# Установите права
sudo chown -R 1000:1000 /var/lib/2getpro
sudo chown -R 1000:1000 /var/log/2getpro
```

**2. Настройте переменные окружения:**
```bash
# Скопируйте пример
cp ../../.env.example ../../.env.production

# Отредактируйте файл
vim ../../.env.production
```

**3. Настройте SSL сертификаты:**
```bash
# Поместите сертификаты в директорию
mkdir -p docker/ssl
cp /path/to/cert.pem docker/ssl/
cp /path/to/key.pem docker/ssl/
cp /path/to/chain.pem docker/ssl/
```

**4. Запустите сервисы:**
```bash
cd docker
docker-compose -f docker-compose.prod.yml up -d
```

**5. Проверьте статус:**
```bash
# Статус контейнеров
docker-compose -f docker-compose.prod.yml ps

# Логи
docker-compose -f docker-compose.prod.yml logs -f bot

# Проверка здоровья
curl http://localhost:8081/health
```

#### Управление:
```bash
# Остановка
docker-compose -f docker-compose.prod.yml stop

# Перезапуск
docker-compose -f docker-compose.prod.yml restart bot

# Обновление
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f --tail=100 bot

# Выполнение команд
docker-compose -f docker-compose.prod.yml exec bot python manage.py shell
```

---

### 3. Systemd (Для bare-metal серверов)

#### Предварительные требования:
- Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- Python 3.10+
- PostgreSQL 15+
- Redis 7+
- Nginx

#### Шаги развертывания:

**1. Создайте пользователя:**
```bash
sudo useradd -r -s /bin/bash -d /opt/2getpro-v2 -m 2getpro
```

**2. Установите зависимости:**
```bash
# Python и виртуальное окружение
cd /opt/2getpro-v2
sudo -u 2getpro python3 -m venv venv
sudo -u 2getpro venv/bin/pip install -r requirements.txt
```

**3. Настройте окружение:**
```bash
sudo cp .env.example .env.production
sudo vim .env.production
sudo chown 2getpro:2getpro .env.production
sudo chmod 600 .env.production
```

**4. Настройте скрипты:**
```bash
sudo cp infrastructure/systemd/scripts/*.sh /opt/2getpro-v2/scripts/
sudo chmod +x /opt/2getpro-v2/scripts/*.sh
```

**5. Установите systemd service:**
```bash
sudo cp infrastructure/systemd/2getpro-v2.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable 2getpro-v2
```

**6. Запустите сервис:**
```bash
sudo systemctl start 2getpro-v2
sudo systemctl status 2getpro-v2
```

#### Управление:
```bash
# Статус
sudo systemctl status 2getpro-v2

# Логи
sudo journalctl -u 2getpro-v2 -f

# Перезапуск
sudo systemctl restart 2getpro-v2

# Остановка
sudo systemctl stop 2getpro-v2

# Перезагрузка конфигурации
sudo systemctl reload 2getpro-v2
```

---

## 📊 Мониторинг

### Prometheus

**Доступ:**
- URL: `http://localhost:9090` (или через Ingress)
- Targets: `http://localhost:9090/targets`
- Alerts: `http://localhost:9090/alerts`

**Проверка метрик:**
```bash
# Проверка доступности метрик бота
curl http://localhost:9090/metrics

# Проверка конкретной метрики
curl -G http://localhost:9090/api/v1/query --data-urlencode 'query=bot_requests_total'
```

### Grafana

**Доступ:**
- URL: `http://localhost:3000` (или через Ingress)
- Логин: `admin`
- Пароль: из переменной `GRAFANA_PASSWORD`

**Импорт дашбордов:**
1. Откройте Grafana UI
2. Перейдите в Dashboards → Import
3. Загрузите JSON файлы из `grafana/dashboards/`

### Алерты

Алерты настроены в Prometheus и отправляются через Alertmanager.

**Настройка Alertmanager:**
```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'telegram'

receivers:
  - name: 'telegram'
    telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: YOUR_CHAT_ID
        parse_mode: 'HTML'
```

---

## 🔒 Безопасность

### SSL/TLS сертификаты

**Для Kubernetes (cert-manager):**
```bash
# Установка cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Создание ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

**Для Nginx (Let's Encrypt):**
```bash
# Установка certbot
sudo apt-get install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d webhook.example.com

# Автообновление
sudo certbot renew --dry-run
```

### Firewall

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# iptables
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -j DROP
```

---

## 🔧 Обслуживание

### Бэкапы

**PostgreSQL:**
```bash
# Ручной бэкап
docker-compose exec postgres pg_dump -U 2getpro_user 2getpro_v2 | gzip > backup-$(date +%Y%m%d).sql.gz

# Автоматический бэкап (cron)
0 2 * * * /opt/2getpro-v2/scripts/backup.sh
```

**Redis:**
```bash
# Ручной бэкап
docker-compose exec redis redis-cli BGSAVE

# Копирование RDB файла
docker cp 2getpro-redis:/data/dump.rdb ./backup-redis-$(date +%Y%m%d).rdb
```

### Обновления

**Kubernetes:**
```bash
# Обновление образа
kubectl set image deployment/2getpro-v2-bot bot=2getpro-v2:v2.1.0 -n 2getpro-v2

# Мониторинг обновления
kubectl rollout status deployment/2getpro-v2-bot -n 2getpro-v2
```

**Docker Compose:**
```bash
# Обновление образа
docker-compose -f docker-compose.prod.yml pull bot
docker-compose -f docker-compose.prod.yml up -d bot
```

**Systemd:**
```bash
# Обновление кода
cd /opt/2getpro-v2
sudo -u 2getpro git pull
sudo -u 2getpro venv/bin/pip install -r requirements.txt

# Перезапуск сервиса
sudo systemctl restart 2getpro-v2
```

### Логи

**Kubernetes:**
```bash
# Логи бота
kubectl logs -f deployment/2getpro-v2-bot -n 2getpro-v2

# Логи всех подов
kubectl logs -f -l app=2getpro-v2 -n 2getpro-v2

# Логи за последний час
kubectl logs --since=1h deployment/2getpro-v2-bot -n 2getpro-v2
```

**Docker Compose:**
```bash
# Логи бота
docker-compose -f docker-compose.prod.yml logs -f bot

# Логи всех сервисов
docker-compose -f docker-compose.prod.yml logs -f
```

**Systemd:**
```bash
# Логи сервиса
sudo journalctl -u 2getpro-v2 -f

# Логи за последний час
sudo journalctl -u 2getpro-v2 --since "1 hour ago"
```

---

## 🐛 Troubleshooting

### Бот не запускается

**Проверьте логи:**
```bash
# Kubernetes
kubectl logs deployment/2getpro-v2-bot -n 2getpro-v2

# Docker Compose
docker-compose logs bot

# Systemd
sudo journalctl -u 2getpro-v2 -n 100
```

**Проверьте подключение к БД:**
```bash
# PostgreSQL
psql -h localhost -U 2getpro_user -d 2getpro_v2

# Redis
redis-cli -h localhost ping
```

### Высокая нагрузка

**Проверьте метрики:**
```bash
# CPU и память
kubectl top pods -n 2getpro-v2

# Количество запросов
curl http://localhost:9090/api/v1/query?query=rate(bot_requests_total[5m])
```

**Масштабирование:**
```bash
# Kubernetes
kubectl scale deployment/2getpro-v2-bot --replicas=5 -n 2getpro-v2

# Docker Compose
docker-compose -f docker-compose.prod.yml up -d --scale bot=5
```

### Проблемы с webhook

**Проверьте Nginx:**
```bash
# Статус
sudo systemctl status nginx

# Тест конфигурации
sudo nginx -t

# Логи
sudo tail -f /var/log/nginx/error.log
```

**Проверьте SSL:**
```bash
# Проверка сертификата
openssl s_client -connect webhook.example.com:443 -servername webhook.example.com

# Проверка через curl
curl -v https://webhook.example.com/health
```

---

## 📚 Дополнительные ресурсы

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)

---

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи
2. Проверьте метрики в Grafana
3. Проверьте алерты в Prometheus
4. Обратитесь к документации в `docs/`

---

**Версия:** 2.0.0  
**Последнее обновление:** 2024-01-27