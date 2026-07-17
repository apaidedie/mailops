# UI workflow polish A–E (scheme B pass)

## Goal

在已落地的 **UI 精简方案 B** 之上，按 **A→B→C→D→E** 顺序把 MailOps 管理台打磨成「工作流优先」的运维界面：默认只露出日常主路径，高级能力折叠保留，去掉指挥台/营销文案噪音。

**用户价值：** 运营人员每天导入账号、管分组、读邮件/取验证码、按需配外部 API 时更少扫读、更少点错入口。

## Background（confirmed）

- 产品定位：聚合已购 Outlook + 临时邮箱；自建分组做渠道管理；可选统一外部 API。
- 方案 B 已合入 `main`（`4e735f6e` 等）：概览 KPI 化、设置长文案收敛、Token OAuth 工具移除、刷新日志保留。
- 仍有噪音：统一邮箱 `unified-command-center`、外部 API `external-api-command-center`、多处 kicker/Setup Path、导入弹窗长 hint、设置页残留 `form-hint`。
- 邮箱页三种模式：`unified` / `standard` / `compact`（`templates/index.html` view switcher）。
- 发布约束：不破坏前端合同测试；`main` 保持 Code Quality + Python Tests + Docker 绿灯；SonarCloud 不作为发布门禁。

## Approach

**方案 1（已批准）：逐面薄打磨 A→E**

每面同一套规则：

1. 去掉默认营销/指挥台文案与 kicker  
2. 默认只露出主操作  
3. 高级筛选/诊断/契约/能力矩阵默认折叠  
4. 空状态改为「下一步动作」  
5. 前端合同测试同步，避免 CI 回归  

## Child task map

| Order | Child | Focus |
|------:|-------|--------|
| 1 | `07-18-ui-polish-a-mailbox` | 邮箱主路径：分组 → 账号 → 读信/验证码 |
| 2 | `07-18-ui-polish-b-import-groups` | 导入与分组：批量导入、分组管理、空状态 |
| 3 | `07-18-ui-polish-c-unified-temp` | 统一邮箱 + 临时邮箱：指挥台降噪、列表/预览优先 |
| 4 | `07-18-ui-polish-d-external-api` | 外部 API：密钥 + 核心开关；诊断折叠 |
| 5 | `07-18-ui-polish-e-shell` | 全局壳层：导航 IA、顶栏、词表收口 |

父任务负责跨子任务验收与最终一致性；**实现与 `task.py start` 以当前子任务为单位**（先 A）。

## Requirements

### Shared (all children)

- **R1** 默认视图无 page subtitle / kicker / “command center / 指挥台” 营销语（Demo strip 除外）。
- **R2** 长说明文案不默认展示：`title` 提示，或折叠「说明」区块。
- **R3** 高级能力默认折叠，不删除功能与后端 API。
- **R4** 空状态给出单一主行动作（导入 / 选组 / 获取邮件 / 配置 API 等）。
- **R5** 每子任务合入后：相关前端合同测试更新并通过；不缩小目标以通过部分检查。
- **R6** 缓存破坏：若改 CSS，递增 `ui-modern.css?v=…`。

### A — Mailbox main path

- **A1** standard/compact：默认焦点为「选分组 → 账号列表 → 邮件列表/详情/验证码」。
- **A2** 顶栏操作保留主路径按钮（添加账号等）；诊断类不默认抢占。
- **A3** 去掉邮箱主路径上多余副标题与说明条。

### B — Import & groups

- **B1** 导入弹窗：格式 hint 收敛（可折叠或短一行），不挡导入主操作。
- **B2** 分组列表/空状态：引导「新建分组」或「导入账号」。
- **B3** 分组代理/验证码等高级字段保持可用但不抢默认视线。

### C — Unified & temp email

- **C1** 统一邮箱默认：搜索 + 列表 + 预览；command center / Setup Path / 能力矩阵默认折叠或降为次要。
- **C2** 临时邮箱默认：创建/列表 + 获取邮件 + 预览。
- **C3** 文案去「指挥台/运营态势」类营销词。

### D — External API

- **D1** 默认：API Key + 核心开关。
- **D2** smoke / contract / workflow playbooks 默认折叠。
- **D3** 不改外部 API 后端契约。

### E — Global shell

- **E1** 导航分区与标签与日常工作流一致（概览 / 邮箱工作台 / Token / 系统）。
- **E2** 顶栏标题无营销副标题；mailbox 模式切换文案务实。
- **E3** i18n 中 command-center 类键值随 UI 清理，避免中英仍写「指挥台」。

## Acceptance Criteria

### Parent (all children done)

- [x] A–E 子任务均完成且各自验收通过  
- [x] 默认打开管理台：无指挥台营销壳；主路径 3 步内可达导入/读信  
- [x] 高级诊断/契约仍可展开使用  
- [x] `main`：Code Quality + Python Tests + Docker Build/Push 绿灯（合入后验证）

### Per child

见各子任务 `prd.md`。

## Out of scope

- 后端 API 契约变更  
- 删除刷新日志、号池、外部 API 能力  
- 整套设计系统重做 / 新前端框架  
- SonarCloud 专项治理  
- OAuth Token 工具恢复  

## Open questions

（无阻塞项；方案 1 已批准。实现阶段若发现合同测试大面积耦合 command-center DOM，在子任务 design 中记录并最小化 DOM 兼容层。）
