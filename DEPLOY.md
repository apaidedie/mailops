# MailOps 部署指南

面向个人/小团队的 **Docker 一键部署**。

## 前置

- Docker Engine + Docker Compose v2
- 本机端口可用（默认主机 `5001` → 容器 `5000`）

## 30 秒启动

```bash
# 1. 克隆
git clone https://github.com/apaidedie/mailops.git
cd mailops

# 2. 环境变量
cp .env.example .env
# 必须设置 SECRET_KEY（Windows PowerShell 示例）：
# python -c "import secrets; print(secrets.token_hex(32))"
# 编辑 .env 填入 SECRET_KEY，并按需修改 LOGIN_PASSWORD

# 3. 构建并后台启动
docker compose up -d --build

# 4. 打开
# http://localhost:5001
```

登录密码默认见 `.env` 中 `LOGIN_PASSWORD`（示例为 `admin123`，生产务必修改）。

## 常用命令

```bash
docker compose logs -f app      # 日志
docker compose ps               # 状态
docker compose restart app      # 重启
docker compose down             # 停止（数据在 ./data 保留）
docker compose up -d --build    # 拉代码后重建
```

## 数据与配置

| 路径 | 说明 |
|------|------|
| `./data` | SQLite 与持久数据 |
| `./plugins` | 临时邮箱 Provider 插件 |
| `./.runtime` | 运行时配置/缓存 |
| `.env` | 密钥与环境变量（勿提交） |

## 可选：Watchtower 一键更新

默认不启动 watchtower（`profiles: [update]`）。需要时：

```bash
docker compose --profile update up -d
```

## 仅构建镜像

```bash
docker build -t mailops:local .
docker run -d --name mailops -p 5001:5000 \
  -v "$(pwd)/data:/app/data" \
  --env-file .env \
  mailops:local
```

## 健康检查

容器内：`GET /healthz`（不要用需登录的 `/`）。

## 安全清单

1. 强随机 `SECRET_KEY`，部署后不要更换（用于加密库内敏感字段）
2. 强 `LOGIN_PASSWORD`
3. 公网暴露时配合 HTTPS 反代
4. 勿把 `.env` 提交到 Git
