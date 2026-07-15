# MailOps 部署指南

## 推荐：服务器拉取镜像（一键）

镜像：`ghcr.io/apaidedie/mailops:latest`  
由 GitHub Actions 在 `main` 推送后自动构建。

### 1. 准备目录与环境变量

```bash
mkdir -p mailops && cd mailops
curl -fsSL https://raw.githubusercontent.com/apaidedie/mailops/main/docker-compose.server.yml -o docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/apaidedie/mailops/main/.env.example -o .env
```

编辑 `.env`，至少设置：

```bash
SECRET_KEY=<用 python -c "import secrets; print(secrets.token_hex(32))" 生成>
LOGIN_PASSWORD=<你的强密码>
APP_PORT=5001   # 可选，主机端口
```

### 2. 拉取并启动

若 GHCR 包为 **public**（首次构建后到 GitHub → Packages 设为 public）：

```bash
docker compose pull
docker compose up -d
```

若包为 private，先登录：

```bash
echo YOUR_GITHUB_PAT | docker login ghcr.io -u apaidedie --password-stdin
docker compose pull
docker compose up -d
```

打开：`http://服务器IP:5001`

### 3. 常用命令

```bash
docker compose logs -f
docker compose ps
docker compose pull && docker compose up -d   # 更新到最新镜像
docker compose down
```

数据在 `./data`，停容器不丢库。

---

## 本机源码构建（开发 / 无 GHCR 时）

```bash
git clone https://github.com/apaidedie/mailops.git
cd mailops
cp .env.example .env   # 设置 SECRET_KEY
docker compose up -d --build
# http://localhost:5001
```

默认构建本地镜像 `mailops:local`（见根目录 `docker-compose.yml`）。

---

## 健康检查

容器探针：`GET /healthz`（不要用需登录的 `/`）。

## 安全

1. 强随机 `SECRET_KEY`，部署后不要随意更换  
2. 修改默认 `LOGIN_PASSWORD`  
3. 公网请挂 HTTPS 反代  
4. 勿提交 `.env`  

## 镜像与 CI

- 仓库：https://github.com/apaidedie/mailops  
- 镜像：`ghcr.io/apaidedie/mailops:latest`  
- 工作流：`.github/workflows/docker-build-push.yml`（`main` 推送 / 手动 `workflow_dispatch`）

Dependabot 的 PR 若只因 **SonarCloud 未配置密钥** 失败，可先关闭；与镜像构建无直接关系。镜像是否成功看 **Actions → Build and Push Docker Image**。
