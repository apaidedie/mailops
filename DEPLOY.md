# MailOps 部署指南

## 服务器一键部署

镜像：`ghcr.io/apaidedie/mailops:latest`

```bash
mkdir -p mailops && cd mailops
# 下载 compose（或复制仓库里的 docker-compose.yml）
curl -fsSL https://raw.githubusercontent.com/apaidedie/mailops/main/docker-compose.yml -o docker-compose.yml

# 编辑 docker-compose.yml：把 SECRET_KEY 改成随机值
# python -c "import secrets; print(secrets.token_hex(32))"

docker compose pull
docker compose up -d
# http://服务器IP:5001
```

### 常用命令

```bash
docker compose logs -f
docker compose pull && docker compose up -d   # 更新
docker compose down
```

数据目录：`./data`

数据目录：`./data`

### 低内存服务器（≤2GB RAM）部署指南

2GB 服务器部署时建议以下调整（`docker-compose.yml` 已内置默认启用）：

| 配置 | 默认值 | 低内存建议 | 说明 |
|------|--------|-----------|------|
| `GUNICORN_THREADS` | 8 | **4** | 减少线程降低上下文切换和栈内存 |
| `GUNICORN_MAX_REQUESTS` | 0（关闭） | **500** | worker 回收防止长期运行内存泄漏 |
| `GUNICORN_MAX_REQUESTS_JITTER` | 0 | **50** | 抖动避免所有 worker 同时回收 |
| 系统 swap | 无 | **≥2GB** | 强烈建议添加 swap，防止 OOM killer 终止容器 |

```bash
# 添加 2GB swap（一次性操作，重启持久）
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

如果 2GB 服务器同时运行其他服务（Nginx、数据库等），建议在 `docker-compose.yml` 中添加内存限制：

```yaml
    deploy:
      resources:
        limits:
          memory: 1G
```

## 本机源码构建（可选）

```bash
git clone https://github.com/apaidedie/mailops.git && cd mailops
docker compose -f docker-compose.build.yml up -d --build
```

## 健康检查

`GET /healthz`

## 安全

1. 强随机 `SECRET_KEY`，部署后不要随意更换  
2. 修改默认 `LOGIN_PASSWORD`  
3. 公网请挂 HTTPS  
4. 勿提交 `.env`  
