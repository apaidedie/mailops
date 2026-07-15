# Deployment info Settings surface paint guard

## Goal
Always warm lastDeploymentInfo soft cache, but paint warnings/update-method radios only while Settings surface is active.

## Done
- [x] applyDeploymentInfo({ paint }) option
- [x] loadDeploymentInfo paintSettingsChrome via isSettingsSurfaceActive
- [x] language soft-repaint gated to Settings surface
- [x] contracts + quality-guidelines
- [x] node --check + unittest + git diff --check
