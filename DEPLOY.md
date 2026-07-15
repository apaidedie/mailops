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
