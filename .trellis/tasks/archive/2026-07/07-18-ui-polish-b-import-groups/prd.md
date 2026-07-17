# B: import and groups polish

## Goal

导入账号与分组管理默认清爽：主操作突出，格式说明不挡路，空状态可行动。

## Depends on

- After A preferred (can start after A ships)

## Requirements

- **B1** 导入弹窗：长 format hint 收敛为短提示或可展开「格式说明」  
- **B2** 分组空状态：引导新建分组 / 导入  
- **B3** 分组高级字段（代理、验证码策略）保留但不抢默认视线  
- **B4** 合同测试同步  

## Acceptance Criteria

- [x] 打开导入弹窗可直接粘贴导入，不被多段 essay 淹没（格式说明默认折叠）  
- [x] 无分组时有明确主按钮（A 已交付 + 本面保留）  
- [x] 全部导入模式/策略仍可用；分组高级字段收入「高级选项」  
- [x] 相关测试绿灯

## Out of scope

- 新导入格式协议  
- 后端导入 API 变更  
