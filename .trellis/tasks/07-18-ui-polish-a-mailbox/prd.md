# A: mailbox main path polish

## Goal

把 **邮箱页 standard/compact 主路径** 打磨成：选分组 → 选账号 → 读信/取验证码，默认无营销壳、无诊断抢占。

## Depends on

- Parent: `07-18-ui-workflow-polish-ae`（方案 1）
- Order: first child; no peer dependency

## Requirements

- **A1** standard/compact 默认焦点：分组栏 + 账号列表 + 邮件区  
- **A2** 顶栏：模式切换 + 主操作（添加账号/导出/刷新按现有逻辑）；不新增营销副标题  
- **A3** 去掉邮箱主路径多余说明条/副标题  
- **A4** 邮件/账号空状态给单一下一步（如导入账号、选择分组、获取邮件）  
- **A5** 本面相关前端合同测试更新并通过  

## Acceptance Criteria

- [x] standard 模式：无默认 kicker/指挥台文案  
- [x] 从侧栏进「统一邮箱」后，在账号视图下可完成选组→账号→邮件  
- [x] compact 模式仍可用且无新增噪音  
- [x] 相关 unittest 合同绿灯  
- [x] 空状态 CTA：添加分组 / 导入账号 / 获取邮件（`65118786`）

## Out of scope

- 统一邮箱 command center 大改（属 C）  
- 导入弹窗 hint（属 B）  
- 导航全局改名（属 E）  
