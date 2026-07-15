// split from state.js → polling.js
        function isAutoPollingEnabledSetting(value) {
            return value === true || value === 'true';
        }

        // 应用标准轮询设置到内部变量（Phase 2: 仅更新变量，实际轮询由统一引擎处理）
        function applyPollingSettings(settings, { restart = false } = {}) {
            // [Phase 3 兼容] 任一开关开启即启用轮询：
            // - enable_auto_polling：合并后的统一开关
            // - enable_compact_auto_poll：deprecated 旧字段，历史用户可能只设置了这个
            autoPollingEnabled = isAutoPollingEnabledSetting(settings.enable_auto_polling)
                || isAutoPollingEnabledSetting(settings.enable_compact_auto_poll);
            maxPollingCount = parseIntegerSetting(settings.polling_count, 5);
            pollingInterval = parseIntegerSetting(settings.polling_interval, 10);
            // [Phase 3] 合并后统一由标准字段驱动引擎
            if (typeof applyPollSettings === 'function') {
                applyPollSettings({
                    enabled: autoPollingEnabled,
                    interval: pollingInterval,
                    maxCount: maxPollingCount
                });
            }
        }

