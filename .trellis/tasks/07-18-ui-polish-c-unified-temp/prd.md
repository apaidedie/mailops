# C: unified and temp email polish

## Goal

统一邮箱与临时邮箱默认变成「搜/列表/预览」工作台；服务状态与能力矩阵降为高级折叠。

## Depends on

- After B preferred

## Requirements

- **C1** 统一邮箱：command center / Setup Path / 能力矩阵默认折叠或次要  
- **C2** 临时邮箱：列表 + 获取邮件 + 预览优先  
- **C3** 去掉「指挥台/运营态势」类默认文案  
- **C4** 保留 DOM id 以兼容 JS；仅改可见性与文案  
- **C5** 合同测试同步  

## Acceptance Criteria

- [x] 进入统一工作台默认看到收件工作区；邮箱/高级互斥切换  
- [x] 高级服务信息在「高级」页可访问；kicker 默认隐藏  
- [x] 临时邮箱空状态 CTA：创建 / 获取邮件  
- [x] 相关测试绿灯

## Out of scope

- Provider 插件协议变更  
- 外部 API 页（属 D）  
