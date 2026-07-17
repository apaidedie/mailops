# MailOps

[English](./README.en.md) · [Docker 部署](./DEPLOY.md) · [贡献指南](./CONTRIBUTING.md) · [安全策略](./SECURITY.md) · [支持](./SUPPORT.md)

**MailOps**（前身 Outlook Email Plus）是一款面向个人与团队的**注册 / 验证场景**邮箱运维工作台。

与通用邮箱客户端不同，它聚焦注册机、验证码提取、邮箱池与外部 API。你可以把 Outlook OAuth、普通 IMAP、邮箱池、Provider 临时邮箱和自动化接口放在同一套目录与契约下；其它项目可通过 `X-API-Key`、OpenAPI 与 `integration_manifest` 接入。

仓库：https://github.com/apaidedie/mailops

**快速入口**：

- [Project Launchpad](./docs/project-launchpad.md)：两分钟了解项目定位、支持邮箱来源、启动路径、外部接入与验证门禁。
- [Runtime Readiness](./docs/runtime-readiness.md)：当前版本的本地启动、Provider 配置、外部 API 和页面检查交付说明。
- [快速开始](#快速开始)：用 Docker 或本地 Python 跑起来。
- [外部接口与邮箱池集成](#外部接口与邮箱池集成)：给注册机、批量任务或其他服务接入统一邮箱能力。
- [External Integration Quickstart](./docs/external-integration-quickstart.md)：外部服务接入、只读 smoke 检查和统一邮箱会话流程。
- [Provider Onboarding Guide](./docs/provider-onboarding.md)：接入 Mail.tm 兼容服务、DuckMail、TempMail.lol、Emailnator 或未来 Provider。
- [浏览器扩展](#浏览器扩展)：在注册页一键领取邮箱并提取验证码。
- [界面预览](#界面预览)：查看当前后台工作台截图。

### 为什么是 OutlookMail Plus

- **专为注册而生**：尽量减少注册流程中不必要的操作。你可以一键复制邮箱地址；在注册页发送验证邮件后，回到管理器点击“验证码”，即可自动拉取最新验证邮件，并用正则快速提取验证码或验证链接，尽量减少等待。
- **更轻、更专注**：舍弃发件等非核心能力，界面更清爽，所有设计都围绕“把注册跑通”。
- **导入兼容更广**：支持主流邮箱导入（Gmail、QQ、163 等），也支持自定义 IMAP 服务器。即使是自建邮箱也能使用；内置 CF Worker 临时邮箱，支持多域配置与 Admin Key 加密，大幅降低注册场景的隐私泄露风险。
- **支持自动化**：对外提供接口，支持批量自动化注册流程；邮箱池支持 `project_key` 项目隔离领取。对于长期邮箱，在领取阶段显式传入 `project_key + caller_id + task_id` 时，同项目成功账号不会被重复分配，`claim-complete(result=success)` 后会直接回到 `available`，并可被其他项目立即复用；临时邮箱 / `cloudflare_temp_mail` 继续沿用旧语义。获取接码与释放邮箱等能力一应俱全。
- **第三方通知**：支持第三方渠道通知，当前已接入 Telegram；重点邮箱收到邮件可自动推送提醒。

简而言之，OutlookMail Plus 是一款为“注册流程”打造的邮箱管理器。

## 演示站点

演示站点：https://demo.outlookmailplus.tech/
登录密码：`12345678`

站点内置 10 个邮箱账号用于演示，数据会定期重置。请勿删除演示账号或将其用于个人用途。

演示涵盖本项目的主要功能（Telegram 推送因需要额外配置，演示站未启用）。




## 界面预览

当前仓库已包含部分截图，后续将继续补充更多演示图片。

![仪表盘](img/仪表盘.png)
![邮箱界面](img/邮箱界面.png)
![提取验证码](img/提取验证码.png)
![设置界面](img/设置界面.png)


## 版本亮点

当前稳定版本：`v2.7.0`

### 近期版本速览

| 版本 | 日期 | 核心新功能 |
|------|------|-----------|
| **v2.2.0** | 2026-04 | 🔌 **临时邮箱 Provider 插件化**：支持第三方插件动态安装/卸载/配置，内置 Cloudflare / 兼容临时邮箱桥接 / Moemail，Provider 设置与域名选择解耦；浏览器扩展新增本地个人信息生成器与完整 Jest 测试覆盖 |
| **v2.1.0** | 2026-04 | 📊 **数据概览大盘**：5 Tab 统一看板（总览 / 验证码提取 / 对外 API / 邮箱池 / 系统活动），新增 `verification_extract_logs` 统一观测链路，并修复浏览器扩展 API Key 复制与 overview i18n/实时刷新问题 |
| **v2.0.0** | 2026-04 | 🌐 **浏览器扩展**（Chrome/Edge MV3）：一键申领邮箱 → 自动提取验证码/链接 → 完成/释放，无需切换标签页；后端新增 `chrome-extension://` CORS 跨域支持 |
| **v1.19.0** | 2026-04 | 🔧 刷新失败提示结构化增强（错误码 + 可执行步骤 + trace 反馈指引）；Selected 账号刷新提前失败修复（Issue #45） |
| **v1.18.0** | 2026-04 | 🔄 邮箱池**项目成功复用**：显式携带 `project_key + caller_id + task_id` 时，success 后直接回到 `available`，支持跨项目立即复用（DB v22）|
| **v1.17.0** | 2026-04 | 🪝 **Webhook 通知通道**：全局单 URL 配置，与 Email/Telegram 并存；X-API-Key 随机生成快捷入口 |
| **v1.16.0** | 2026-04 | 🔑 OAuth Token 工具升级：新增"获取授权链接"模式，稳定支持跨环境授权 |
| **v1.15.0** | 2026-04 | 🤖 **AI 验证码增强**：系统级 AI fallback（双低置信才触发），固定 JSON 契约；**邮箱别名**（`+tag`）自动识别与回溯 |
| **v1.13.0** | 2026-04 | ⚡ **一键热更新**：Watchtower（推荐）和 Docker API 双模式，自动检测新版本弹出提示 |
| **v1.11.0** | 2026-04 | 🏊 **邮箱池项目隔离**（`project_key`）；CF Worker 多域 + Admin Key 加密；前端账号列表分页；统一轮询引擎 |
| **v1.9.0** | 2026-03 | 🌐 **双语界面**（中/英）；统一通知分发（Email + Telegram）；演示站点登录密码保护 |

---

### v2.1.0 — 数据概览大盘与观测增强

- 新增 5 Tab 数据概览大盘，替换旧 dashboard
- 新增 `verification_extract_logs`，统一观测普通账号 / 临时邮箱 / external API 提取链路
- 修复浏览器扩展“API 无效”的真实根因：复制脱敏 API Key 与 external pool / pool_access 前置条件认知偏差
- overview 前端补齐实时重拉与完整 i18n，页头 / Tab / hover note / timeline 现与主体卡片保持一致

### v2.0.0 — 浏览器扩展（新）

`browser-extension/` 目录包含 Chrome/Edge Manifest V3 扩展，详见 [浏览器扩展](#浏览器扩展) 章节。

### v1.15.0–v1.16.0 — OAuth Token 获取工具

- 新增独立 Token 工具窗口，以**兼容账号导入模式**获取 Microsoft refresh token
- 当前模式固定面向个人 Microsoft 账号：Public Client、`tenant=consumers`、不支持 `client_secret`
- Azure 应用注册的 **Supported account types** 应选择 **Accounts in any identity provider or organizational directory and personal Microsoft accounts**；仅组织目录会报 `unauthorized_client`，而 **Personal Microsoft accounts only** 会在写入前 `/common` 验证阶段报 `AADSTS9002331`
- 如果 Azure 门户在切换 Supported account types 时提示 `Property api.requestedAccessTokenVersion is invalid`，请到 **Manifest** 中把 `api.requestedAccessTokenVersion` 改为 `2`
- 如果已经开启 Public Client 仍然报"必须包含 `client_secret`"，说明当前回调仍被 Azure 视为机密 Web 客户端；此时应改用 **Mobile and desktop applications** 平台的 public redirect（如 `http://localhost`），并在工具里走手动粘贴回调 URL
- 如果遇到 `AADSTS70000`（scope 未授权/失效），优先检查"授权时 scope"和"验证时 scope"是否一致，并重新执行一次 **强制 Consent** 授权
- Graph 场景建议最小权限：**offline_access + Mail.Read + User.Read**；如需 IMAP 再额外补 **Office 365 Exchange Online → IMAP.AccessAsUser.All**
- 支持 Graph / IMAP Scope 预设、错误引导、JWT audience/scope 诊断；前端默认推荐 **Graph 邮件预设**（后端环境变量 fallback 保持 IMAP 兼容 Scope）
- 页面内置 Azure 应用注册快速指引折叠卡片（5 步）与教程入口：<https://real-caption-6d1.notion.site/OutlooKMailplus-token-344463aed7e680099380dc324ecdf1c9?source=copy_link>
- 支持一键写入已有 Outlook 账号或创建新账号，写入前自动验证 refresh token，并拒绝不兼容配置

### v1.13.0 — 一键更新

- 支持两种更新方式：Watchtower（推荐）和 Docker API 自更新（高级）
- 自动检测 GitHub 最新版本，界面弹出更新提示
- 完整的部署信息检测：镜像标签、本地构建、Watchtower 连通性等
- Watchtower 已是最新版本智能检测（基于 Watchtower 同步行为）
- Docker API 模式 digest 预检查，相同版本不触发无效更新

### v1.11.0 — 邮箱池 & 前端增强

- **邮箱池项目隔离**：`project_key` 防止同项目重复领取（DB v17）
- **CF Worker 临时邮箱多域支持**：设置页配置多个域名，"同步域名"按钮一键刷新
- **Admin Key 加密存储**：`cf_worker_admin_key` 以 `enc:` 前缀加密写入数据库（DB v18）
- **账号列表前端分页**：每页 50 条，大量账号时列表加载更流畅
- **统一轮询引擎**：标准模式与简洁模式合并为单一 `poll-engine`，修复竞态与状态积压

## 核心能力

- 多邮箱账号管理
  支持 Outlook OAuth、普通 IMAP 邮箱和 CF Worker 临时邮箱（多域配置，Admin Key 加密存储）
- 批量导入与分组整理
  支持批量导入、标签、搜索、分组、导出
- 邮件读取与提取
  支持验证码、链接、原文内容读取
- 邮箱池调度
  支持可领取、释放、完成、冷却恢复、过期回收等状态流转；长期邮箱支持 `project_key` 项目维度成功复用：同项目按 success 记录防重复领取，`success` 后回到 `available`，跨项目可立即复用；显式临时邮箱 provider 支持池空时动态创建并领取，`auto` 不会触发上游创建
- 受控对外接口
  支持 `X-API-Key` 鉴权、多调用方 Key 管理、邮箱范围授权、IP 白名单和速率限制
- 通知能力
  支持业务邮件通知、Telegram 推送和测试发送
- 演示站点保护
  可通过环境变量锁定登录密码修改入口，避免访客在设置页改后台密码

## 项目结构

```text
outlook_web/          Flask 应用主体（controllers / routes / services / repositories）
templates/            页面模板
static/               前端脚本与样式
data/                 SQLite 数据与运行时文件
tests/                自动化测试
web_outlook_app.py    兼容入口
```

## 快速开始

### Docker 部署（推荐）

完整说明见 **[DEPLOY.md](./DEPLOY.md)**。

**服务器一键（`docker-compose.yml`）**

```bash
mkdir -p mailops && cd mailops
curl -fsSL https://raw.githubusercontent.com/apaidedie/mailops/main/docker-compose.yml -o docker-compose.yml
# 编辑文件：修改 SECRET_KEY（必填）与 LOGIN_PASSWORD
docker compose pull && docker compose up -d
# http://服务器:5001
```

镜像：`ghcr.io/apaidedie/mailops:latest`  
本机构建：`docker compose -f docker-compose.build.yml up -d --build`

#### ClawCloud / 反向代理部署注意事项

- 健康检查请显式使用 `GET /healthz`，不要依赖 `/`、`/login` 或 302 跳转链路；本项目首页 `/` 受登录保护，会重定向到 `/login`
- `no healthy upstream` 表示反向代理当前没有健康后端，不等于应用一定是“代码崩溃”；更新后若持续出现，优先查看**新容器启动日志**与平台事件
- 若平台事件出现 `Stopping container`、`FailedKillPod`、`KillPodSandbox DeadlineExceeded`，说明故障至少包含平台侧 Pod 停止/回收异常，不能只根据应用日志下结论
- 本项目默认使用 SQLite + 持久卷，更新时建议保持**单实例**；若新旧实例短时并发访问同一数据库文件，启动阶段的迁移或文件锁等待可能导致健康检查超时
- `TEMP_EMAIL_UPSTREAM_READ_FAILED` 与 `no healthy upstream` 需要分开理解：前者是临时邮箱上游读取失败，后者是入口层前面没有健康应用实例

### 本地运行

```bash
python -m venv .venv
pip install -r requirements.txt
python web_outlook_app.py
```

如果你还没有真实 Outlook/IMAP 或临时邮箱 Provider 凭据，可以先生成本地演示库，直接查看统一邮箱、临时邮箱、邮箱池和外部 API 看板效果：

```bash
python scripts/seed_demo_workspace.py --reset
```

然后使用生成的 `output/demo/outlook-email-plus-demo.db` 启动：

```powershell
$env:DATABASE_PATH="output/demo/outlook-email-plus-demo.db"
$env:SCHEDULER_AUTOSTART="false"
python web_outlook_app.py
```

### 运行测试

```bash
python -m unittest discover -s tests -v
```

发布、部署交接或接入外部服务前，先跑本地只读就绪门禁：

```bash
python scripts/project_readiness_check.py
python scripts/project_readiness_check.py --format json
```

## 常用环境变量

- `SECRET_KEY`
  会话与敏感字段加密密钥，必须配置
- `LOGIN_PASSWORD`
  初始后台登录密码，首次启动后会写入数据库并哈希存储
- `ALLOW_LOGIN_PASSWORD_CHANGE`
  是否允许在设置页修改登录密码。演示站点建议设为 `false`
- `DATABASE_PATH`
  SQLite 数据库路径，默认 `data/outlook_accounts.db`
- `PORT` / `HOST`
  Web 服务监听地址
- `SCHEDULER_AUTOSTART`
  是否自动启动后台调度器
- `GPTMAIL_BASE_URL`
  兼容临时邮箱桥接沿用的服务根地址，例如 `https://mail.chatgpt.org.uk`。变量名保留 `GPTMAIL_*` 是为了兼容旧部署；如果误填 API 文档页地址如 `/zh/api`，运行时会自动归一到服务根地址
- `GPTMAIL_API_KEY`
  兼容临时邮箱桥接沿用的 API Key；留空时该桥接会显示为缺配置。新部署也可以优先使用 `mail_tm`、`duckmail`、`tempmail_lol`、`emailnator`、`cloudflare_temp_mail` 或插件 provider
- `TEMP_MAIL_PROVIDER`
  临时邮箱运行时 Provider 覆盖。可选 `legacy_bridge`、`mail_tm`、`duckmail`、`tempmail_lol`、`emailnator`、`cloudflare_temp_mail`；留空时使用设置页保存值。`legacy_bridge` 用于自建或兼容临时邮箱桥接
- `EXTERNAL_POOL_DEFAULT_PROVIDER`
  外部邮箱池默认领取来源。`POST /api/v1/external/pool/claim-random` 不传 `provider` 时使用该值；可设为 `auto`、普通账号 provider 或临时邮箱 provider，留空时保持自动领取
- `ACTIVE_MAILBOX_PROVIDERS`
  启用邮箱来源白名单。留空表示全部启用；填写后仅暴露并使用这些 provider，支持逗号或换行分隔，例如 `duckmail,mail_tm`、`imap`、`legacy_bridge`。兼容别名 `gptmail`、`legacy_gptmail`、`temp_mail` 仍会归一到兼容临时邮箱桥接
- `OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE`
  Provider 选择配置文件路径，支持 JSON/TOML，可声明 `temp_mail_provider`、`pool_default_provider` 和 `active_mailbox_providers`；优先级低于环境变量，高于设置页保存值
- `MAILTM_API_BASE`
  Mail.tm 兼容 API 地址，默认 `https://api.mail.tm`
- `DUCKMAIL_API_BASE` / `DUCKMAIL_BEARER_TOKEN`
  DuckMail API 地址与 Bearer Token
- `TEMPMAIL_LOL_API_KEY`（兼容 `TEMP_MAIL_LOL_API_KEY`）
  TempMail.lol API Key；不填时仍可使用公开免费接口能力
- `EMAILNATOR_API_KEY` / `EMAILNATOR_EMAIL_TYPES`
  Emailnator RapidAPI Key 与邮箱类型 JSON 数组
- `CF_WORKER_BASE_URL`（设置页对应 `cf_worker_base_url`）
  Cloudflare Temp Email Worker 地址
- `CF_WORKER_ADMIN_KEY`（设置页对应 `cf_worker_admin_key`）
  Cloudflare Worker Admin 密码；建议仅通过设置页保存，系统会加密存储

外部项目可先通过 `GET /api/v1/external/capabilities` 或 `GET /api/v1/external/providers` 读取顶层 `integration_manifest`，它是最适合自动化接入的机器可读启动契约：`auth` 固定说明 `X-API-Key` 与 `<your-api-key>` 占位，`discovery.recommended_sequence` 给出 capabilities、providers、mailboxes 的发现顺序，`selection` 说明 env、provider config file、settings、默认值的优先级和请求字段，`deployment` 给出 env/config 模板，`providers[*].env` 与 `providers[*].settings` 给出各 provider 的配置 key。密钥字段名可以出现，例如 `DUCKMAIL_BEARER_TOKEN`，但 secret hint 的 `value` 永远是空字符串；非密钥默认值如 `MAILTM_API_BASE=https://api.mail.tm` 和 `DUCKMAIL_API_BASE=https://api.duckmail.sbs` 会作为默认值返回。旧版 `/api/external/*` 路径仍作为 legacy alias 兼容已有客户端。

新增或对接邮箱来源时，建议先看 [Provider Onboarding Guide](./docs/provider-onboarding.md)。运行时的 `integration_manifest`、`provider_integration_guide` 和统一邮箱目录 `provider_context` 也会返回 `documentation` 对象，外部项目可以从接口里发现这份人类指南、API 文档页、OpenAPI 契约、`.env.example` 和 JSON/TOML 配置示例。

`provider_integration_guide` 仍保留为更详细的按 provider 分组接入指南。每个 catalog 项都会返回 `selection`、`configuration` 和 `deployment`，其中 `deployment` 直接给出激活来源、设为默认临时邮箱、设为默认领取来源、请求字段和所需环境变量/settings 的机器可读写法。顶层 `deployment_profile` 会聚合所有 provider 的可选值、必需/可选/敏感环境变量、settings key 和按 provider 激活示例；其中 `templates` 直接返回可写入 `.env` 的环境变量模板，以及只用于 provider 选择的 JSON/TOML 模板。顶层 `selection_policy` 是外部调用方的统一选择契约，可读取 `source_priority` 判断 env、provider config file、settings、默认值的优先级，读取 `scopes` 判断启用白名单、默认临时邮箱、默认领取来源和单次请求应使用哪个字段，读取 `templates` 直接生成部署配置。`provider_integration_guide` 会把上述 catalog、部署模板、选择策略、诊断状态、别名和 endpoint 汇总成一份按 provider 分组的接入指南；它会说明 DuckMail 这类 mail.tm 兼容服务需要哪些 env key、请求体该传 `provider` 还是 `provider_name`、如何设置运行时默认值和池默认值，并只暴露密钥字段名，不回显密钥值。`provider_diagnostics` 会返回本地就绪状态，区分 `ready`、`needs_config` 和 `inactive`，并在 `defaults` 中报告 `TEMP_MAIL_PROVIDER` 与 `EXTERNAL_POOL_DEFAULT_PROVIDER` 是否指向有效且当前启用的 provider；该诊断只看本地设置、环境变量和白名单，不请求上游。如需显式探测临时邮箱上游，可调用 `GET /api/v1/external/providers/{kind}/{provider}/health?probe_network=true`，未带 `probe_network=true` 时只返回本地就绪信息。登录后的后台设置页使用同源会话接口 `GET /api/providers/{kind}/{provider}/health?probe_network=true`，不要把对外 API Key 放到浏览器里调用 external 接口。`POST /api/v1/external/pool/claim-random` 的 `provider` 可使用该 catalog 中的普通邮箱 provider、临时邮箱 provider 或 `auto`；不传 `provider` 时会读取 `EXTERNAL_POOL_DEFAULT_PROVIDER` 或设置项 `pool_default_provider`，两者都为空则保持自动领取。`ACTIVE_MAILBOX_PROVIDERS` 或设置项 `active_mailbox_providers` 可把当前实例收窄为只使用指定来源，catalog、`auto` 领取、显式 provider 领取和任务临时邮箱申请都会遵守该白名单。显式传入临时邮箱 provider 且池内没有可用邮箱时，系统会按该 provider 动态创建并直接领取。`auto` 不会触发动态创建，避免无意消耗上游资源。`POST /api/v1/external/temp-emails/apply` 的 `provider_name` 可用来精确选择新建任务邮箱来源。

外部项目也可以用 `X-API-Key` 打开 `GET /api/v1/external/docs` 查看内置 API 文档页，或调用 `GET /api/v1/external/openapi.json` 获取 OpenAPI 3.1 契约，用于生成客户端、校验响应字段和发现端点；其中 `x-capabilities.integration_manifest` 会同步返回上述启动契约。API 文档页和 OpenAPI 契约都只描述外部接口形状，不回显 provider 密钥或 API Key 明文。

登录后的管理端可调用 `GET /api/mailboxes` 获取统一邮箱目录；外部项目可用 `X-API-Key` 调用 `GET /api/v1/external/mailboxes` 获取同一套目录 DTO，外层按 external API 统一返回 `{success, code, message, data}`。该接口把 Outlook/IMAP 账号和用户可见临时邮箱归一为同一种 mailbox DTO，支持 `kind=all|account|temp`、`status`、`read_capability=all|graph|imap|temp_provider`、`action=all|read_messages|refresh_auth|delete_remote_mailbox|delete_message|clear_messages`、`provider=all|provider_key`、`search`、`sort=updated_desc|created_desc|email_asc|provider_asc|status_asc`、`page`、`page_size`，并返回 `facets.kinds`、`facets.statuses`、`facets.read_capabilities`、`facets.providers`、`facets.actions`、`provider_context`、`contract.version=1` 与 `{kind}:{source_id}` 格式的稳定 `id`。固定筛选 facets 会按当前上下文统计每个契约枚举值的数量，但不会被自身的精确筛选自我收窄，例如 `facets.statuses` 不受当前 `status` 过滤影响，`facets.actions` 不受当前 `action` 过滤影响，适合直接渲染带数量的筛选项。每个 item 还会返回 `actions` 与 `action_contract`，其中 `actions` 是当前邮箱支持的操作能力布尔表，`action_contract.external` 复用统一 external read contract 并预填当前邮箱的 `email` 查询参数，`action_contract.internal.open_mailbox` 则告诉后台 UI 应进入普通账号页还是临时邮箱页。`provider_context` 会给出当前默认来源、激活白名单、provider 诊断、选择策略、`provider_integration_guide` 和可写入 `.env`/JSON/TOML 的部署模板，外部项目可以据此通过环境变量或配置文件切换邮箱来源。多 Key 配置了 `allowed_emails` 时，外部目录会在统计、facets 和分页前收窄普通账号记录；用户可见临时邮箱仍按当前读信权限可见，任务临时邮箱不会进入目录。它只返回展示和工作台编排需要的元数据，不回显 refresh token、IMAP 密码、临时邮箱 task token、consumer key 或上游密钥；真正读信仍通过 `action_contract.external` 指向的 `/api/v1/external/*` 读信接口，管理端旧页面可继续使用 `action_contract.internal` 指向的 `/api/emails/*` 或 `/api/temp-emails/*`。

`.env.example` 已列出这些 provider 选择开关；使用 `docker-compose.yml` 部署时，`TEMP_MAIL_PROVIDER`、`EXTERNAL_POOL_DEFAULT_PROVIDER`、`ACTIVE_MAILBOX_PROVIDERS`、`OUTLOOK_EMAIL_PROVIDER_CONFIG_FILE` 和各 provider 凭据会从 `.env` 自动注入容器。配置优先级为环境变量、provider 配置文件、设置页保存值、内置默认值。配置文件示例见 `.runtime/providers.example.json` 与 `.runtime/providers.example.toml`。

### 一键更新相关

- `WATCHTOWER_HTTP_API_TOKEN`
  Watchtower API 鉴权令牌。**可留空**，留空时 app 和 watchtower 两边自动使用同一内置默认值，开箱即用；生产环境建议设置随机强密码
- `WATCHTOWER_API_URL`
  Watchtower API 地址，默认 `http://watchtower:8080`（Docker 内部网络，通常无需修改）
- `DOCKER_SELF_UPDATE_ALLOW`
  是否启用 Docker API 自更新功能，默认 `false`。⚠️ 启用后容器可访问 Docker API，存在安全风险
- `DOCKER_IMAGE`
  当前容器镜像名（可选，用于部署信息检测）

> **安全提示**：Docker API 自更新需要挂载 `/var/run/docker.sock`，这会授予容器完全的 Docker API 访问权限。生产环境建议使用 Watchtower 方式。

## 通知能力说明

### 邮件通知

如果你准备启用“邮件通知”，需要额外配置 SMTP。邮件通知与 Telegram、临时邮箱 provider 是独立链路，不能互相替代。

最少需要配置：

- `EMAIL_NOTIFICATION_SMTP_HOST`
- `EMAIL_NOTIFICATION_FROM`

常见可选配置：

- `EMAIL_NOTIFICATION_SMTP_PORT`
- `EMAIL_NOTIFICATION_SMTP_USERNAME`
- `EMAIL_NOTIFICATION_SMTP_PASSWORD`
- `EMAIL_NOTIFICATION_SMTP_USE_TLS`
- `EMAIL_NOTIFICATION_SMTP_USE_SSL`
- `EMAIL_NOTIFICATION_SMTP_TIMEOUT`

示例：

```env
EMAIL_NOTIFICATION_SMTP_HOST=smtp.qq.com
EMAIL_NOTIFICATION_SMTP_PORT=465
EMAIL_NOTIFICATION_FROM=your_account@qq.com
EMAIL_NOTIFICATION_SMTP_USERNAME=your_account@qq.com
EMAIL_NOTIFICATION_SMTP_PASSWORD=your_smtp_auth_code
EMAIL_NOTIFICATION_SMTP_USE_SSL=true
EMAIL_NOTIFICATION_SMTP_USE_TLS=false
EMAIL_NOTIFICATION_SMTP_TIMEOUT=15
```

注意：

- 设置页中的测试邮件遵循“先保存，再测试”
- 测试接口不会直接读取输入框临时值
- 系统只会读取已保存的 `email_notification_recipient`

### Telegram 推送

项目支持在设置页配置：

- `telegram_bot_token`
- `telegram_chat_id`
- `telegram_poll_interval`

当前版本中，Telegram 推送与业务邮件通知已经统一接入通知分发链路。

## 外部接口与邮箱池集成

如果你要把本项目接入注册机、脚本平台或其他自动化系统，当前推荐方式是受控外部接口：

最短接入路径见 [External Integration Quickstart](./docs/external-integration-quickstart.md)。它包含只读 smoke 检查、`integration_manifest` 发现、`/api/v1/external/mailbox-sessions/start` 统一会话启动和生命周期关闭示例。

需要直接嵌入外部服务时，可以从 [`examples/external_api_python_client.py`](./examples/external_api_python_client.py) 开始。它是零第三方依赖的可复制 Python starter，支持 discovery、统一 mailbox session 启动、验证码读取和 finally 生命周期关闭；CLI 的 `discover` 子命令只读，`verification-code` 子命令会启动并关闭一次邮箱会话。

- 路径前缀：`/api/v1/external/*`（`/api/external/*` 保留为 legacy alias）
- 鉴权头：`X-API-Key`
- 邮箱池接口：`/api/v1/external/pool/*`

当前外部接口支持：

- 单 Key 鉴权
- 多 Key 配置
- 按调用方限制邮箱范围
- 公网模式白名单与速率限制
- 可禁用原文读取、长轮询等高风险端点
- `/api/v1/external/docs` 可打开内置外部 API 文档页，适合人工查看认证、provider 选择和 mailbox session 工作流
- `/api/v1/external/openapi.json` 可获取外部 API 的 OpenAPI 3.1 机器可读契约
- `/api/v1/external/capabilities` 可发现统一邮箱目录、provider、读信、邮箱池和任务临时邮箱契约
- `integration_manifest` 可从 capabilities、providers 或 OpenAPI `x-capabilities` 读取，用于生成安全的外部接入 env/config 启动配置
- `/api/v1/external/mailboxes` 可按 provider、类型、状态、读取方式、操作能力、关键词和固定排序获取外部可见的统一邮箱目录

注意：

- 旧匿名 `/api/pool/*` 已移除
- 生产环境建议开启受控公网模式并配置白名单

## 浏览器扩展

`browser-extension/` 目录包含配套的 Chrome / Edge 扩展（Manifest V3），提供「申领邮箱 → 获取验证码/链接 → 完成/释放」一站式快捷面板，无需切换标签页。

详细说明见 [browser-extension/README.md](./browser-extension/README.md)。

### 项目 Key（Project Key）

项目 Key 用于**邮箱池的多租户隔离**：不同业务/项目的申领互不干扰，配合 `caller_id + task_id` 还能在同项目内防止重复分配。

- **不填**：从公共邮箱池随机申领
- **填写**：只在该项目的邮箱中申领；`success` 完成后邮箱立即回到 `available`，可被其他项目复用

### 完成 vs 释放

完成和释放都会结束当前任务，区别在于邮箱的后续状态：

| 操作 | 邮箱状态 | 适用场景 |
|------|---------|---------|
| **释放（Release）** | → `available`（立即可再申领） | 注册失败、误领、测试归还 |
| **完成（Complete）** | → `used`（已用，默认不再分配） | 注册成功、验证码已使用 |

> 启用项目复用时，`complete(result=success)` + 显式 `project_key` 路径会直接回到 `available`，支持跨项目立即复用。

## 演示站点建议

如果你要公开一个演示站点给其他人访问，建议至少这样配置：

```env
LOGIN_PASSWORD=your-strong-password
ALLOW_LOGIN_PASSWORD_CHANGE=false
```

- 站点仍然可以登录
- 访客无法在“系统设置”里改掉后台登录密码



## 项目文档

- [Project Launchpad](./docs/project-launchpad.md)
- [Runtime Readiness](./docs/runtime-readiness.md)
- [External Integration Quickstart](./docs/external-integration-quickstart.md)
- [Provider Onboarding Guide](./docs/provider-onboarding.md)
- [注册与邮箱池接口文档](./docs/registration-mail-pool-api.zh.md)
- [Registration Worker and Mail Pool API](./docs/registration-mail-pool-api.en.md)
- [临时邮箱 Provider 插件接入说明](./docs/temp-mail-provider-plugin-guide.md)
- [临时邮箱 Provider 插件接入提示词](./docs/temp-mail-provider-plugin-prompt.md)

如果你要对接注册机、批量工作流或新增邮箱来源，优先看 Provider Onboarding Guide。

如果你要新增一个临时邮箱 Provider 插件，优先看上面的「插件接入说明」与「插件接入提示词」。

## 致谢

本项目基于以下技术与服务能力构建：

- Flask
- SQLite
- Microsoft Graph API
- IMAP
- APScheduler

  
 外部友链：https://linux.do/


也参考了以下项目的思路：

- [assast/outlookEmail](https://github.com/assast/outlookEmail)
- [gblaowang-i/MailAggregator_Pro](https://github.com/gblaowang-i/MailAggregator_Pro)

## 许可证

Apache License 2.0

## 联系方式

如果你在使用过程中遇到问题，或有合作意向，欢迎通过邮件联系：[outlookmailplus@163.com](mailto:outlookmailplus@163.com)
