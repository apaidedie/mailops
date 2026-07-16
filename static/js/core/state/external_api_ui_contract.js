// split from external_api_ui.js → contract.js
        async function loadExternalApiContractCheck(forceRefresh = false) {
            const force = Boolean(forceRefresh);
            // Soft re-entry: always return warm cache; paint only on api-security tab.
            if (!force && externalApiContractCheckCache) {
                if (isCurrentApiSecuritySurface()) {
                    renderExternalApiCommandCenter(externalApiSettingsSnapshot, externalApiCommandRenderState || 'ready');
                }
                return externalApiContractCheckCache;
            }
            // Soft joins any in-flight. Force joins only force in-flight;
            // force supersedes soft so explicit recheck starts a true network GET.
            if (externalApiContractCheckPromise) {
                if (!force || externalApiContractCheckLoadForce) {
                    return externalApiContractCheckPromise;
                }
                // Abandon soft in-flight bookkeeping; identity check blocks stale apply.
                externalApiContractCheckPromise = null;
                externalApiContractCheckLoadForce = false;
            }

            externalApiContractCheckLoadForce = force;
            externalApiContractCheckState = { status: 'loading', error: null };
            if (isCurrentApiSecuritySurface()) {
                renderExternalApiCommandCenter(externalApiSettingsSnapshot, externalApiCommandRenderState || 'ready');
            }

            const request = fetch('/api/settings/external-api/contract-check')
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    if (externalApiContractCheckPromise !== request) {
                        return externalApiContractCheckCache;
                    }
                    const report = data && typeof data.contract_check === 'object' ? data.contract_check : null;
                    if (!report) throw new Error('contract_check_missing');
                    // Always warm soft cache; paint only while still on api-security.
                    externalApiContractCheckCache = report;
                    externalApiContractCheckState = { status: String(report.status || 'pass'), error: null };
                    if (isCurrentApiSecuritySurface()) {
                        renderExternalApiCommandCenter(externalApiSettingsSnapshot, externalApiCommandRenderState || 'ready');
                    }
                    return report;
                })
                .catch(error => {
                    if (externalApiContractCheckPromise !== request) {
                        return externalApiContractCheckCache;
                    }
                    console.warn('加载外部 API 契约校验失败:', error);
                    externalApiContractCheckCache = null;
                    externalApiContractCheckState = { status: 'error', error: error && error.message ? error.message : 'contract_check_failed' };
                    if (isCurrentApiSecuritySurface()) {
                        renderExternalApiCommandCenter(externalApiSettingsSnapshot, externalApiCommandRenderState || 'ready');
                    }
                    return null;
                })
                .finally(() => {
                    if (externalApiContractCheckPromise === request) {
                        externalApiContractCheckPromise = null;
                        externalApiContractCheckLoadForce = false;
                    }
                });
            externalApiContractCheckPromise = request;
            return request;
        }

        function getExternalIntegrationManifestWorkflows() {
            const manifest = getExternalIntegrationManifest();
            return Array.isArray(manifest.workflows)
                ? manifest.workflows.filter(item => item && typeof item === 'object' && String(item.key || '').trim() && Array.isArray(item.steps))
                : [];
        }

        function getExternalApiQuickstartText() {
            const quickstart = getExternalIntegrationQuickstart();
            if (!quickstart || !Object.keys(quickstart).length) return '';
            const auth = getExternalQuickstartAuth();
            const sequence = getExternalQuickstartSequence();
            const selectors = getExternalQuickstartSelectors();
            const requests = getExternalQuickstartRequests();
            const lines = [
                '# Outlook Email Plus External API Quickstart',
                `# Auth: ${auth.header}: ${auth.placeholder}`,
                '',
                '[sequence]',
                ...(sequence.length ? sequence.map(item => {
                    const method = String(item.method || 'GET').trim().toUpperCase() || 'GET';
                    const endpoint = appendExternalApiStarterQuery(item.endpoint, item.query);
                    return `${method} ${endpoint}`.trim();
                }) : [
                    `GET ${externalApiCanonicalPath('/capabilities')}`,
                    `GET ${externalApiCanonicalPath('/providers')}`,
                    `GET ${externalApiCanonicalPath('/mailboxes')}?kind=all&provider=all&sort=updated_desc`
                ]),
                '',
                '[provider selectors]',
            ];
            Object.keys(selectors).forEach(key => {
                const selector = selectors[key] && typeof selectors[key] === 'object' ? selectors[key] : {};
                const field = String(selector.field || selector.request_field || '').trim();
                const allowed = Array.isArray(selector.allowed_values) && selector.allowed_values.length
                    ? ` (${selector.allowed_values.join(', ')})`
                    : '';
                if (field) lines.push(`${key}: ${field}${allowed}`);
            });
            [
                ['pool_claim', requests.pool_claim],
                ['task_temp_apply', requests.task_temp_apply],
                ['mailbox_session_start', requests.mailbox_session_start],
                ['mailbox_session_read', requests.mailbox_session_read],
                ['mailbox_session_close', requests.mailbox_session_close],
            ].forEach(([key, request]) => {
                if (!request) return;
                lines.push('', `[${key}]`, getExternalQuickstartRequestLine(request));
                const bodyText = formatExternalQuickstartJson(request.body);
                if (bodyText) lines.push(bodyText);
            });
            return `${lines.filter(line => line !== undefined && line !== null).join('\n')}\n`;
        }

        function getExternalApiStarterManifestEndpoint(manifestEndpoints, key, fallback) {
            const endpoints = manifestEndpoints && typeof manifestEndpoints === 'object' ? manifestEndpoints : {};
            const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
            return String(endpoints[key] || endpoints[camelKey] || fallback || '').trim();
        }

        function getExternalApiWorkflowFallbacks(endpointMap = getExternalApiStarterEndpointMap()) {
            return [
                {
                    key: 'start_mailbox_session',
                    label: 'Start mailbox session',
                    description: 'Create a provider-neutral readable mailbox session, read messages or verification data, then close the session lifecycle.',
                    steps: [
                        { key: 'start_session', label: 'Start session', method: 'POST', endpoint: endpointMap.mailboxSessionStart, auth: 'api_key', request: { body_fields: ['caller_id', 'task_id', 'source_strategy', 'provider', 'provider_name', 'email_domain', 'project_key', 'prefix', 'domain'], required_body_fields: ['caller_id', 'task_id'], source_strategy_values: ['pool_first', 'task_temp_first', 'pool_only', 'task_temp_only'] }, response: { field: 'data', session_type_field: 'session_type', email_field: 'email', lifecycle_field: 'lifecycle' }, next: { success: 'read_session' } },
                        { key: 'read_session', label: 'Read session mailbox', method: 'POST', endpoint: endpointMap.mailboxSessionRead, auth: 'api_key', request: { body_fields: ['session_type', 'read_action', 'caller_id', 'task_id', 'email', 'claim_token', 'task_token', 'folder', 'code_regex', 'since_minutes'], required_body_fields: ['session_type', 'read_action'], read_action_values: ['messages', 'latest_message', 'message_detail', 'message_raw', 'verification_code', 'verification_link', 'wait_message'] }, response: { field: 'data.result' }, next: { success: 'close_session' } },
                        { key: 'close_session', label: 'Close session', method: 'POST', endpoint: endpointMap.mailboxSessionClose, auth: 'api_key', request: { body_fields: ['session_type', 'account_id', 'claim_token', 'task_token', 'caller_id', 'task_id', 'result', 'detail'], required_body_fields: ['session_type'] }, response: { field: 'data' } }
                    ]
                },
                {
                    key: 'discover_external_api',
                    label: 'Discover external API',
                    description: 'Fetch capabilities, provider catalog, and mailbox directory before choosing a mailbox source.',
                    steps: [
                        { key: 'capabilities', label: 'Read capabilities', method: 'GET', endpoint: endpointMap.capabilities, auth: 'api_key', response: { field: 'integration_manifest' }, next: { success: 'providers' } },
                        { key: 'providers', label: 'Read providers', method: 'GET', endpoint: endpointMap.providers, auth: 'api_key', response: { field: 'integration_manifest.providers' }, next: { success: 'mailboxes' } },
                        { key: 'mailboxes', label: 'Read mailbox directory', method: 'GET', endpoint: endpointMap.mailboxes, auth: 'api_key', request: { query: { kind: 'all', provider: 'all', sort: 'updated_desc' } }, response: { field: 'mailboxes' } }
                    ]
                },
                {
                    key: 'browse_mailbox_directory',
                    label: 'Browse mailbox directory',
                    description: 'Inspect account and temp mailboxes, then read messages or verification codes.',
                    steps: [
                        { key: 'list_mailboxes', label: 'List mailboxes', method: 'GET', endpoint: endpointMap.mailboxes, auth: 'api_key', request: { query_fields: ['kind', 'status', 'read_capability', 'action', 'provider', 'search', 'sort', 'page', 'page_size'] }, response: { field: 'mailboxes' }, next: { success: 'read_messages' } },
                        { key: 'read_messages', label: 'Read messages', method: 'GET', endpoint: endpointMap.messages, auth: 'api_key', request: { query_fields: ['email', 'claim_token', 'folder'] }, response: { field: 'emails' } },
                        { key: 'read_verification_code', label: 'Read verification code', method: 'GET', endpoint: endpointMap.verificationCode, auth: 'api_key', request: { query_fields: ['email', 'claim_token', 'folder', 'code_regex'] }, response: { field: 'verification_code' } }
                    ]
                },
                {
                    key: 'claim_pool_mailbox',
                    label: 'Claim pool mailbox',
                    description: 'Claim a reusable mailbox, read registration mail, then complete or release the claim.',
                    steps: [
                        { key: 'claim_random', label: 'Claim mailbox', method: 'POST', endpoint: endpointMap.poolClaimRandom, auth: 'api_key', request: { body_fields: ['caller_id', 'task_id', 'provider', 'email_domain', 'project_key'], required_body_fields: ['caller_id', 'task_id'], provider_selector: { field: 'provider', optional: true } }, response: { field: 'data', email_field: 'email', claim_token_field: 'claim_token' }, next: { success: 'read_messages' } },
                        { key: 'read_messages', label: 'Read messages', method: 'GET', endpoint: endpointMap.messages, auth: 'api_key', request: { query_fields: ['email', 'claim_token', 'folder'] }, response: { field: 'emails' }, next: { success: 'read_verification_code' } },
                        { key: 'read_verification_code', label: 'Read verification code', method: 'GET', endpoint: endpointMap.verificationCode, auth: 'api_key', request: { query_fields: ['email', 'claim_token', 'folder', 'code_regex'] }, response: { field: 'verification_code' }, next: { success: 'complete_claim' } },
                        { key: 'complete_claim', label: 'Complete claim', method: 'POST', endpoint: endpointMap.poolClaimComplete, auth: 'api_key', request: { body_fields: ['account_id', 'claim_token', 'caller_id', 'task_id', 'result', 'detail'] }, response: { field: 'data' } },
                        { key: 'release_claim', label: 'Release claim', method: 'POST', endpoint: endpointMap.poolClaimRelease, auth: 'api_key', request: { body_fields: ['account_id', 'claim_token', 'caller_id', 'task_id', 'reason'] }, response: { field: 'data' } }
                    ]
                },
                {
                    key: 'create_task_temp_mailbox',
                    label: 'Create task temp mailbox',
                    description: 'Create a task-scoped temp mailbox, read registration mail, then finish the task mailbox lifecycle.',
                    steps: [
                        { key: 'apply_task_mailbox', label: 'Create mailbox', method: 'POST', endpoint: endpointMap.tempMailApply, auth: 'api_key', request: { body_fields: ['caller_id', 'task_id', 'prefix', 'domain', 'provider_name'], required_body_fields: ['caller_id', 'task_id'], provider_selector: { field: 'provider_name', optional: true } }, response: { field: 'data', email_field: 'email', task_token_field: 'task_token' }, next: { success: 'read_messages' } },
                        { key: 'read_messages', label: 'Read messages', method: 'GET', endpoint: endpointMap.messages, auth: 'api_key', request: { query_fields: ['email', 'claim_token', 'folder'] }, response: { field: 'emails' }, next: { success: 'read_verification_code' } },
                        { key: 'read_verification_code', label: 'Read verification code', method: 'GET', endpoint: endpointMap.verificationCode, auth: 'api_key', request: { query_fields: ['email', 'claim_token', 'folder', 'code_regex'] }, response: { field: 'verification_code' }, next: { success: 'finish_task_mailbox' } },
                        { key: 'finish_task_mailbox', label: 'Finish task mailbox', method: 'POST', endpoint: endpointMap.tempMailFinish, auth: 'api_key', request: { path_fields: ['task_token'], body_fields: ['result', 'detail'] }, response: { field: 'data' } }
                    ]
                }
            ];
        }

        function normalizeExternalApiWorkflow(workflow) {
            const item = workflow && typeof workflow === 'object' ? workflow : {};
            const key = String(item.key || '').trim();
            const steps = Array.isArray(item.steps)
                ? item.steps.filter(step => step && typeof step === 'object' && String(step.endpoint || '').trim())
                : [];
            if (!key || !steps.length) return null;
            return {
                key,
                label: String(item.label || key).trim() || key,
                description: String(item.description || '').trim(),
                steps
            };
        }

        function getExternalApiWorkflowPlaybooks() {
            const manifestWorkflows = getExternalIntegrationManifestWorkflows()
                .map(normalizeExternalApiWorkflow)
                .filter(Boolean);
            if (manifestWorkflows.length) return manifestWorkflows;
            return getExternalApiWorkflowFallbacks()
                .map(normalizeExternalApiWorkflow)
                .filter(Boolean);
        }

        function normalizeExternalApiWorkflowKey(key, workflows = getExternalApiWorkflowPlaybooks()) {
            const normalized = String(key || '').trim();
            if (workflows.some(item => item.key === normalized)) return normalized;
            if (workflows.some(item => item.key === 'claim_pool_mailbox')) return 'claim_pool_mailbox';
            return workflows.length ? workflows[0].key : 'claim_pool_mailbox';
        }

        function formatExternalApiWorkflowValue(value) {
            if (Array.isArray(value)) return value.map(formatExternalApiWorkflowValue).filter(Boolean).join(', ');
            if (value && typeof value === 'object') {
                return Object.keys(value)
                    .map(key => `${key}=${formatExternalApiWorkflowValue(value[key])}`)
                    .filter(item => item.trim() !== '=')
                    .join(', ');
            }
            return String(value === undefined || value === null ? '' : value).trim();
        }

        function getExternalApiWorkflowRequestHints(step) {
            const request = step && step.request && typeof step.request === 'object' ? step.request : {};
            const hints = [];
            ['path_fields', 'query_fields', 'body_fields', 'required_body_fields'].forEach(fieldName => {
                const value = formatExternalApiWorkflowValue(request[fieldName]);
                if (value) hints.push(`${fieldName}: ${value}`);
            });
            if (request.query && typeof request.query === 'object') {
                const value = formatExternalApiWorkflowValue(request.query);
                if (value) hints.push(`query: ${value}`);
            }
            const providerSelector = request.provider_selector && typeof request.provider_selector === 'object' ? request.provider_selector : null;
            if (providerSelector && providerSelector.field) {
                const allowedValues = formatExternalApiWorkflowValue(providerSelector.allowed_values);
                hints.push(`provider selector: ${providerSelector.field}${allowedValues ? ` (${allowedValues})` : ''}`);
            }
            return hints;
        }

        function getExternalApiWorkflowResponseHints(step) {
            const response = step && step.response && typeof step.response === 'object' ? step.response : {};
            return Object.keys(response).map(key => `${key}: ${formatExternalApiWorkflowValue(response[key])}`).filter(item => item.trim() !== ':');
        }

        function getExternalApiWorkflowNextHints(step) {
            const next = step && step.next && typeof step.next === 'object' ? step.next : {};
            return Object.keys(next).map(key => `${key}: ${formatExternalApiWorkflowValue(next[key])}`).filter(item => item.trim() !== ':');
        }

        function renderExternalApiWorkflowSelector(workflow, selectedKey) {
            const active = workflow.key === selectedKey;
            const primaryEndpoint = workflow.steps && workflow.steps[0] ? String(workflow.steps[0].endpoint || '').trim() : '';
            return [
                `<button type="button" class="external-api-workflow-tab${active ? ' active' : ''}" data-external-api-workflow-key="${escapeHtml(workflow.key)}" aria-pressed="${active ? 'true' : 'false'}">`,
                    `<span>${escapeHtml(translateAppTextLocal(workflow.label))}</span>`,
                    `<small>${escapeHtml(workflow.steps.length)} ${escapeHtml(translateAppTextLocal('步'))}${primaryEndpoint ? ` · ${escapeHtml(primaryEndpoint)}` : ''}</small>`,
                '</button>'
            ].join('');
        }

        function renderExternalApiWorkflowHintList(items) {
            const values = Array.isArray(items) ? items.filter(Boolean) : [];
            if (!values.length) return '';
            return `<div class="external-api-workflow-hints">${values.map(item => `<span>${escapeHtml(item)}</span>`).join('')}</div>`;
        }

        function renderExternalApiWorkflowStep(step, index) {
            const item = step && typeof step === 'object' ? step : {};
            const method = String(item.method || 'GET').trim().toUpperCase() || 'GET';
            const endpoint = String(item.endpoint || '').trim();
            const label = String(item.label || item.key || `Step ${index + 1}`).trim();
            const description = String(item.description || '').trim();
            const requestHints = getExternalApiWorkflowRequestHints(item);
            const responseHints = getExternalApiWorkflowResponseHints(item);
            const nextHints = getExternalApiWorkflowNextHints(item);
            return [
                '<div class="external-api-workflow-step">',
                    '<div class="external-api-workflow-step-main">',
                        `<span class="external-api-workflow-index">${index + 1}</span>`,
                        '<div class="external-api-workflow-step-copy">',
                            `<div class="external-api-workflow-step-title">${escapeHtml(translateAppTextLocal(label))}</div>`,
                            description ? `<div class="external-api-workflow-step-desc">${escapeHtml(translateAppTextLocal(description))}</div>` : '',
                            '<div class="external-api-workflow-endpoint-line">',
                                `<span class="external-api-command-method">${escapeHtml(method)}</span>`,
                                `<code>${escapeHtml(endpoint)}</code>`,
                            '</div>',
                            renderExternalApiWorkflowHintList(requestHints),
                            renderExternalApiWorkflowHintList(responseHints),
                            renderExternalApiWorkflowHintList(nextHints),
                        '</div>',
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderExternalApiWorkflowPlaybooks(workflows = getExternalApiWorkflowPlaybooks()) {
            if (!workflows.length) {
                return `<div class="external-api-workflow-playbooks"><div class="external-api-command-empty">${escapeHtml(translateAppTextLocal('暂无 workflow playbooks'))}</div></div>`;
            }
            externalApiWorkflowKey = normalizeExternalApiWorkflowKey(externalApiWorkflowKey, workflows);
            const selectedWorkflow = workflows.find(item => item.key === externalApiWorkflowKey) || workflows[0];
            return [
                '<div class="external-api-workflow-playbooks">',
                    '<div class="external-api-workflow-head">',
                        '<div>',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('工作流 Playbooks'))}</div>`,
                            `<div class="external-api-workflow-subtitle">${escapeHtml(translateAppTextLocal('从当前 integration_manifest 读取端到端接入步骤'))}</div>`,
                        '</div>',
                        `<button type="button" class="external-api-command-copy external-api-workflow-copy" data-external-api-workflow-copy>${escapeHtml(translateAppTextLocal('复制工作流'))}</button>`,
                    '</div>',
                    '<div class="external-api-workflow-body">',
                        `<div class="external-api-workflow-tabs" role="group" aria-label="${escapeHtml(translateAppTextLocal('外部接入工作流'))}">${workflows.map(item => renderExternalApiWorkflowSelector(item, selectedWorkflow.key)).join('')}</div>`,
                        '<div class="external-api-workflow-detail">',
                            `<div class="external-api-workflow-detail-title">${escapeHtml(translateAppTextLocal(selectedWorkflow.label))}</div>`,
                            selectedWorkflow.description ? `<div class="external-api-workflow-detail-desc">${escapeHtml(translateAppTextLocal(selectedWorkflow.description))}</div>` : '',
                            `<div class="external-api-workflow-steps">${selectedWorkflow.steps.map((step, index) => renderExternalApiWorkflowStep(step, index)).join('')}</div>`,
                        '</div>',
                    '</div>',
                '</div>'
            ].join('');
        }

        function getExternalApiWorkflowPlaybookText(workflowKey = externalApiWorkflowKey) {
            const workflows = getExternalApiWorkflowPlaybooks();
            const selectedKey = normalizeExternalApiWorkflowKey(workflowKey, workflows);
            const workflow = workflows.find(item => item.key === selectedKey) || workflows[0];
            if (!workflow) return '';
            const auth = getExternalIntegrationManifestAuth();
            const lines = [
                `# ${workflow.label}`,
                workflow.description ? `# ${workflow.description}` : '',
                `# Auth: ${auth.header}: ${auth.placeholder}`,
                '',
            ].filter(line => line !== '');
            workflow.steps.forEach((step, index) => {
                const method = String(step.method || 'GET').trim().toUpperCase() || 'GET';
                const endpoint = String(step.endpoint || '').trim();
                lines.push(`${index + 1}. ${step.label || step.key || 'Step'} — ${method} ${endpoint}`);
                const requestHints = getExternalApiWorkflowRequestHints(step);
                const responseHints = getExternalApiWorkflowResponseHints(step);
                const nextHints = getExternalApiWorkflowNextHints(step);
                if (requestHints.length) lines.push(`   request: ${requestHints.join(' | ')}`);
                if (responseHints.length) lines.push(`   response: ${responseHints.join(' | ')}`);
                if (nextHints.length) lines.push(`   next: ${nextHints.join(' | ')}`);
            });
            return `${lines.join('\n')}\n`;
        }

        function setExternalApiWorkflowPlaybook(key) {
            externalApiWorkflowKey = normalizeExternalApiWorkflowKey(key);
            const root = document.getElementById('externalApiCommandCenter');
            const currentState = root ? String(root.getAttribute('data-state') || 'ready') : 'ready';
            renderExternalApiCommandCenter(externalApiSettingsSnapshot, currentState === 'loading' ? 'ready' : currentState);
        }

        function getExternalApiMailboxSessionWorkflow() {
            const workflows = getExternalApiWorkflowPlaybooks();
            const workflow = workflows.find(item => item.key === 'start_mailbox_session');
            if (workflow) return workflow;
            return getExternalApiWorkflowFallbacks()
                .map(normalizeExternalApiWorkflow)
                .filter(Boolean)
                .find(item => item.key === 'start_mailbox_session') || null;
        }

        function renderExternalApiQuickstartCockpit() {
            const quickstart = getExternalIntegrationQuickstart();
            if (!quickstart || !Object.keys(quickstart).length) {
                return `<div class="external-api-quickstart-cockpit"><div class="external-api-command-empty">${escapeHtml(translateAppTextLocal('暂无 quickstart 契约'))}</div></div>`;
            }
            const auth = getExternalQuickstartAuth();
            const sequence = getExternalQuickstartSequence();
            const selectors = getExternalQuickstartSelectors();
            const requests = getExternalQuickstartRequests();
            return [
                '<div class="external-api-quickstart-cockpit">',
                    '<div class="external-api-quickstart-head">',
                        '<div>',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('Quickstart'))}</div>`,
                            `<div class="external-api-quickstart-subtitle">${escapeHtml(translateAppTextLocal('最短接入路径'))}</div>`,
                        '</div>',
                        `<button type="button" class="external-api-command-copy external-api-quickstart-copy" data-external-api-quickstart-copy>${escapeHtml(translateAppTextLocal('复制 Quickstart'))}</button>`,
                    '</div>',
                    '<div class="external-api-quickstart-grid">',
                        '<div class="external-api-quickstart-card">',
                            `<span>${escapeHtml(translateAppTextLocal('认证'))}</span>`,
                            `<code>${escapeHtml(auth.header)}: ${escapeHtml(auth.placeholder)}</code>`,
                        '</div>',
                        '<div class="external-api-quickstart-card external-api-quickstart-card-wide">',
                            `<span>${escapeHtml(translateAppTextLocal('发现顺序'))}</span>`,
                            renderExternalQuickstartSequence(sequence),
                        '</div>',
                        '<div class="external-api-quickstart-card">',
                            `<span>${escapeHtml(translateAppTextLocal('Provider selector'))}</span>`,
                            renderExternalQuickstartSelectors(selectors),
                        '</div>',
                    '</div>',
                    '<div class="external-api-quickstart-requests">',
                        renderExternalQuickstartRequestCard('Pool claim', requests.pool_claim),
                        renderExternalQuickstartRequestCard('Task temp mail', requests.task_temp_apply),
                        renderExternalQuickstartRequestCard('Mailbox session start', requests.mailbox_session_start),
                        renderExternalQuickstartRequestCard('Mailbox session read', requests.mailbox_session_read),
                        renderExternalQuickstartRequestCard('Mailbox session close', requests.mailbox_session_close),
                    '</div>',
                '</div>'
            ].join('');
        }

        function renderExternalApiOnboardingChecklist(steps) {
            const safeSteps = Array.isArray(steps) ? steps.filter(item => item && typeof item === 'object') : [];
            if (!safeSteps.length) return '';
            return [
                `<div class="external-api-onboarding" role="list" aria-label="${escapeHtml(translateAppTextLocal('接入检查'))}">`,
                    `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('接入检查'))}</div>`,
                    safeSteps.map(item => [
                        `<div class="external-api-onboarding-step ${escapeHtml(item.tone || 'neutral')}" role="listitem">`,
                            '<span class="external-api-onboarding-dot" aria-hidden="true"></span>',
                            '<div class="external-api-onboarding-main">',
                                `<span class="external-api-onboarding-label">${escapeHtml(translateAppTextLocal(item.label || ''))}</span>`,
                                item.detail ? `<small>${escapeHtml(translateAppTextLocal(item.detail))}</small>` : '',
                            '</div>',
                            `<span class="external-api-onboarding-status">${escapeHtml(translateAppTextLocal(item.status || ''))}</span>`,
                        '</div>'
                    ].join('')).join(''),
                '</div>'
            ].join('');
        }

        function renderExternalApiSmokeCheckPanel() {
            const coverageItems = getExternalApiSmokeCoverageItems();
            const smokeCommand = getExternalApiSmokeCommand();
            return [
                '<div class="external-api-smoke-check">',
                    '<div class="external-api-smoke-grid">',
                        '<div class="external-api-smoke-main">',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('只读接入自检'))}</div>`,
                            `<div class="external-api-smoke-subtitle">${escapeHtml(translateAppTextLocal('部署前复制命令验证 discovery 契约'))}</div>`,
                            '<div class="external-api-smoke-coverage" aria-label="External API smoke coverage">',
                                coverageItems.map(item => [
                                    '<span class="external-api-smoke-coverage-item">',
                                        `<strong>${escapeHtml(translateAppTextLocal(item.label))}</strong>`,
                                        `<code>${escapeHtml(item.endpoint)}</code>`,
                                    '</span>'
                                ].join('')).join(''),
                            '</div>',
                        '</div>',
                        '<div class="external-api-smoke-command-wrap">',
                            `<div class="external-api-smoke-label">${escapeHtml(translateAppTextLocal('只读 discovery 端点'))}</div>`,
                            `<pre class="external-api-command-code external-api-smoke-command"><code>${escapeHtml(smokeCommand)}</code></pre>`,
                            '<div class="external-api-command-actions">',
                                `<button type="button" class="external-api-command-copy external-api-smoke-copy" data-external-api-smoke-copy>${escapeHtml(translateAppTextLocal('复制自检命令'))}</button>`,
                            '</div>',
                        '</div>',
                    '</div>',
                '</div>'
            ].join('');
        }

        function getExternalApiContractCheckSnapshot() {
            const report = externalApiContractCheckCache && typeof externalApiContractCheckCache === 'object'
                ? externalApiContractCheckCache
                : null;
            const state = externalApiContractCheckState && typeof externalApiContractCheckState === 'object'
                ? externalApiContractCheckState
                : { status: 'idle', error: null };
            const summary = report && report.summary && typeof report.summary === 'object' ? report.summary : {};
            const groups = report && Array.isArray(report.groups) ? report.groups : [];
            const nextActions = report && Array.isArray(report.next_actions) ? report.next_actions : [];
            return { report, state, summary, groups, nextActions };
        }

        function getExternalApiContractCheckTone(report, state = externalApiContractCheckState) {
            const stateStatus = String((state && state.status) || '').trim().toLowerCase();
            const reportStatus = String((report && report.status) || '').trim().toLowerCase();
            const status = stateStatus === 'loading' ? 'loading' : (reportStatus || stateStatus || 'idle');
            if (status === 'loading') return { status, badge: 'badge-gray', label: '校验中', tone: 'loading' };
            if (status === 'pass') return { status, badge: 'badge-green', label: '通过', tone: 'pass' };
            if (status === 'fail') return { status, badge: 'badge-gold', label: '需处理', tone: 'fail' };
            if (status === 'error') return { status, badge: 'badge-red', label: '校验失败', tone: 'error' };
            return { status: 'idle', badge: 'badge-gray', label: '暂无契约校验结果', tone: 'idle' };
        }

        function renderExternalApiContractCheckMetric(label, value) {
            return [
                '<div class="external-api-contract-card">',
                    `<span>${escapeHtml(translateAppTextLocal(label))}</span>`,
                    `<strong>${escapeHtml(String(value ?? 0))}</strong>`,
                '</div>'
            ].join('');
        }

        function renderExternalApiContractCheckRow(row) {
            const safeRow = row && typeof row === 'object' ? row : {};
            const passed = safeRow.passed === true;
            const severity = String(safeRow.severity || (passed ? 'info' : 'warning')).trim().toLowerCase() || 'info';
            const detail = safeRow.detail ? `<small>${escapeHtml(String(safeRow.detail))}</small>` : '';
            return [
                `<div class="external-api-contract-row" data-status="${passed ? 'pass' : 'fail'}" data-severity="${escapeHtml(severity)}">`,
                    `<span class="external-api-contract-dot"></span>`,
                    '<div class="external-api-contract-row-main">',
                        `<strong>${escapeHtml(String(safeRow.name || 'contract_check'))}</strong>`,
                        `<small>${escapeHtml(String(safeRow.description || ''))}</small>`,
                        detail,
                    '</div>',
                    `<span class="external-api-contract-severity">${escapeHtml(translateAppTextLocal(passed ? '通过' : severity))}</span>`,
                '</div>'
            ].join('');
        }

        function renderExternalApiContractCheckGroup(group) {
            const safeGroup = group && typeof group === 'object' ? group : {};
            const summary = safeGroup.summary && typeof safeGroup.summary === 'object' ? safeGroup.summary : {};
            const checks = Array.isArray(safeGroup.checks) ? safeGroup.checks : [];
            const failed = Number(summary.failed || 0);
            const status = failed > 0 || String(safeGroup.status || '').toLowerCase() === 'fail' ? 'fail' : 'pass';
            return [
                `<div class="external-api-contract-group" data-status="${escapeHtml(status)}">`,
                    '<div class="external-api-contract-group-head">',
                        '<div>',
                            `<strong>${escapeHtml(String(safeGroup.label || safeGroup.key || 'Contract'))}</strong>`,
                            `<small>${escapeHtml(String(summary.passed || 0))}/${escapeHtml(String(summary.total || checks.length || 0))} ${escapeHtml(translateAppTextLocal('通过项'))}</small>`,
                        '</div>',
                        `<span class="badge ${status === 'pass' ? 'badge-green' : 'badge-gold'}">${escapeHtml(translateAppTextLocal(status === 'pass' ? '通过' : '需处理'))}</span>`,
                    '</div>',
                    checks.length
                        ? `<div class="external-api-contract-rows">${checks.map(renderExternalApiContractCheckRow).join('')}</div>`
                        : `<div class="external-api-command-empty">${escapeHtml(translateAppTextLocal('暂无契约校验结果'))}</div>`,
                '</div>'
            ].join('');
        }

        function renderExternalApiContractCheckAction(action) {
            const safeAction = action && typeof action === 'object' ? action : {};
            return [
                '<div class="external-api-contract-action">',
                    `<span>${escapeHtml(translateAppTextLocal(String(safeAction.priority || 'low')))}</span>`,
                    `<strong>${escapeHtml(String(safeAction.label || safeAction.key || ''))}</strong>`,
                    safeAction.target ? `<code>${escapeHtml(String(safeAction.target))}</code>` : '',
                '</div>'
            ].join('');
        }

        function renderExternalApiContractCheckPanel() {
            const snapshot = getExternalApiContractCheckSnapshot();
            const tone = getExternalApiContractCheckTone(snapshot.report, snapshot.state);
            const summary = snapshot.summary;
            const statusText = snapshot.state.status === 'error' && !snapshot.report
                ? '本地契约校验暂不可用'
                : (snapshot.report ? '服务端只读验证 discovery、OpenAPI、Bundle 和 Provider 合同' : '暂无契约校验结果');
            const safetyItems = [
                { label: '本地只读', passed: snapshot.report ? snapshot.report.local_only === true : tone.status === 'loading' },
                { label: '不探测上游', passed: snapshot.report ? snapshot.report.network_probes === false : tone.status === 'loading' },
                { label: '不变更邮箱', passed: snapshot.report ? snapshot.report.mutation_safe === true : tone.status === 'loading' }
            ];
            const visibleGroups = snapshot.groups.slice(0, 6);
            const visibleActions = snapshot.nextActions.slice(0, 3);
            return [
                `<div class="external-api-contract-check" data-state="${escapeHtml(tone.tone)}" aria-live="polite">`,
                    '<div class="external-api-contract-head">',
                        '<div>',
                            `<div class="external-api-command-section-title">${escapeHtml(translateAppTextLocal('本地契约校验'))}</div>`,
                            `<div class="external-api-contract-subtitle">${escapeHtml(translateAppTextLocal(statusText))}</div>`,
                        '</div>',
                        '<div class="external-api-contract-head-actions">',
                            `<span class="badge ${escapeHtml(tone.badge)}">${escapeHtml(translateAppTextLocal(tone.label))}</span>`,
                            `<button type="button" class="external-api-command-copy external-api-contract-refresh" data-external-api-contract-refresh>${escapeHtml(translateAppTextLocal('重新校验'))}</button>`,
                        '</div>',
                    '</div>',
                    '<div class="external-api-contract-summary">',
                        renderExternalApiContractCheckMetric('检查项', summary.total || 0),
                        renderExternalApiContractCheckMetric('通过项', summary.passed || 0),
                        renderExternalApiContractCheckMetric('失败项', summary.failed || 0),
                        renderExternalApiContractCheckMetric('严重项', summary.critical || 0),
                    '</div>',
                    `<div class="external-api-contract-safety">${safetyItems.map(item => `<span data-pass="${item.passed ? 'true' : 'false'}">${escapeHtml(translateAppTextLocal(item.label))}</span>`).join('')}</div>`,
                    visibleGroups.length
                        ? [
                            '<details class="external-api-contract-details">',
                            `<summary class="external-api-contract-details-summary">${escapeHtml(translateAppTextLocal('查看校验明细'))}<span class="external-api-contract-details-meta">${escapeHtml(String(summary.passed || 0))}/${escapeHtml(String(summary.total || 0))}</span></summary>`,
                            `<div class="external-api-contract-groups">${visibleGroups.map(renderExternalApiContractCheckGroup).join('')}</div>`,
                            '</details>',
                        ].join('')
                        : `<div class="external-api-command-empty">${escapeHtml(translateAppTextLocal(tone.status === 'loading' ? '校验中' : '暂无契约校验结果'))}</div>`,
                    visibleActions.length
                        ? `<div class="external-api-contract-actions">${visibleActions.map(renderExternalApiContractCheckAction).join('')}</div>`
                        : '',
                '</div>'
            ].join('');
        }

