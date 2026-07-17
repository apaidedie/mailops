# D: external API settings polish

## Goal

外部 API 设置默认只露出密钥与核心开关；smoke/contract/playbook 折叠。

## Depends on

- After C preferred

## Requirements

- **D1** 默认可见：API Key + 核心开关  
- **D2** 诊断/契约/workflow 默认折叠  
- **D3** 不改后端外部 API 契约  
- **D4** 合同测试同步  

## Acceptance Criteria

- [x] 设置页外部 API：首屏 API Key 优先  
- [x] 高级工具 / smoke / playbooks / 邮箱来源诊断默认折叠可展开  
- [x] 相关测试绿灯

## Out of scope

- 新 API 端点  
- 密钥存储机制变更  
