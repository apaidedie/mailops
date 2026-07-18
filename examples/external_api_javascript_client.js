"use strict";

const fs = require("node:fs");
const path = require("node:path");

const CANONICAL_EXTERNAL_PREFIX = "/api/v1/external";

const DEFAULT_ENDPOINTS = Object.freeze({
  capabilities: `${CANONICAL_EXTERNAL_PREFIX}/capabilities`,
  integration_bundle: `${CANONICAL_EXTERNAL_PREFIX}/integration-bundle`,
  providers: `${CANONICAL_EXTERNAL_PREFIX}/providers`,
  docs: `${CANONICAL_EXTERNAL_PREFIX}/docs`,
  openapi: `${CANONICAL_EXTERNAL_PREFIX}/openapi.json`,
  mailbox_session_start: `${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start`,
  mailbox_session_read: `${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read`,
  mailbox_session_close: `${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close`,
});

const READ_FILTER_FIELDS = new Set([
  "email",
  "claim_token",
  "task_token",
  "message_id",
  "folder",
  "skip",
  "top",
  "from_contains",
  "subject_contains",
  "since_minutes",
  "code_length",
  "code_regex",
  "code_source",
  "timeout_seconds",
  "poll_interval",
  "mode",
]);

const SECRET_TARGET_PATTERNS = Object.freeze([
  /dk_[0-9a-fA-F]{20,}/,
  /(api[_-]?key|bearer|token|password|secret|jwt|refresh[_-]?token)\s*[:=]\s*(?!<|$)[A-Za-z0-9._~+/=-]{12,}/i,
  /bearer\s+(?!<)[A-Za-z0-9._~+/=-]{12,}/i,
]);

class MailOpsApiError extends Error {
  constructor(message, { status = null, code = null, payload = {} } = {}) {
    super(message);
    this.name = "MailOpsApiError";
    this.status = status;
    this.code = code;
    this.payload = payload || {};
  }
}

function joinUrl(baseUrl, path) {
  return new URL(String(path).replace(/^\/+/, ""), `${String(baseUrl).replace(/\/+$/, "")}/`).toString();
}

async function fetchTransport(method, url, apiKey, body, timeoutSeconds) {
  const headers = { "X-API-Key": apiKey, Accept: "application/json" };
  const init = { method: method.toUpperCase(), headers };
  let timeoutId = null;

  if (body !== null && body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  if (typeof AbortController !== "undefined" && Number.isFinite(timeoutSeconds) && timeoutSeconds > 0) {
    const controller = new AbortController();
    init.signal = controller.signal;
    timeoutId = setTimeout(() => controller.abort(), timeoutSeconds * 1000);
  }

  try {
    const response = await fetch(url, init);
    const raw = await response.text();
    const payload = parseJsonObject(raw || "{}");
    if (!response.ok) {
      throw new MailOpsApiError(`${method.toUpperCase()} ${url} failed with HTTP ${response.status}`, {
        status: response.status,
        code: String(payload.code || "HTTP_ERROR"),
        payload,
      });
    }
    return { status: response.status, payload };
  } catch (error) {
    if (error instanceof MailOpsApiError) {
      throw error;
    }
    throw new MailOpsApiError(`${method.toUpperCase()} ${url} failed: ${error.message}`);
  } finally {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
    }
  }
}

function parseJsonObject(raw) {
  let payload;
  try {
    payload = JSON.parse(raw || "{}");
  } catch (error) {
    throw new MailOpsApiError("response was not valid JSON");
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new MailOpsApiError("response JSON was not an object");
  }
  return payload;
}

function dataOrPayload(payload) {
  return payload && typeof payload.data === "object" && payload.data !== null && !Array.isArray(payload.data)
    ? payload.data
    : payload;
}

function compactJson(value) {
  return JSON.stringify(value, null, 2);
}

function withoutNil(values) {
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== null && value !== undefined));
}

function lifecycleValue(session, key) {
  const lifecycle = session && typeof session.lifecycle === "object" && session.lifecycle !== null ? session.lifecycle : {};
  if (Object.prototype.hasOwnProperty.call(lifecycle, key)) {
    return lifecycle[key];
  }
  return session ? session[key] : undefined;
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function workflowSummary(manifest) {
  const workflows = Array.isArray(manifest.workflows) ? manifest.workflows : [];
  return workflows
    .filter((workflow) => workflow && typeof workflow === "object" && workflow.key)
    .map((workflow) =>
      withoutNil({
        key: String(workflow.key),
        label: workflow.label ? String(workflow.label) : null,
        description: workflow.description ? String(workflow.description) : null,
      }),
    );
}

function summarizeIntegrationBundleActionPlan(bundle) {
  const safeBundle = asObject(bundle);
  const actionPlan = asObject(safeBundle.action_plan);
  if (Object.keys(actionPlan).length === 0) {
    return fallbackActionPlanSummary(safeBundle);
  }

  const items = actionPlanItemSummaries(actionPlan.items);
  return actionPlanSummary({
    source: "action_plan",
    status: textValue(actionPlan.status || safeBundle.status, "unknown"),
    items,
    planSummary: actionPlan.summary,
  });
}

function fallbackActionPlanSummary(bundle) {
  const status = bundleReadinessStatus(bundle);
  const endpoints = asObject(bundle.endpoints);
  const ready = status === "ready";
  const items = [
    {
      key: "inspect_readiness",
      priority: ready ? "medium" : "high",
      status: ready ? "optional" : "action_required",
      blocking: !ready,
      title: "Inspect readiness details",
    },
  ];

  if (ready && endpoints.mailbox_session_start) {
    items.push({
      key: "start_mailbox_session",
      priority: "medium",
      status: "ready",
      blocking: false,
      title: "Start provider-neutral mailbox session",
      endpoint: String(endpoints.mailbox_session_start),
    });
  }

  return actionPlanSummary({ source: "fallback_readiness", status, items, planSummary: null });
}

function actionPlanItemSummaries(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  const items = [];
  for (const rawItem of value) {
    const item = asObject(rawItem);
    if (!item.key) {
      continue;
    }
    const summary = {
      key: String(item.key),
      priority: textValue(item.priority, "medium"),
      status: textValue(item.status, "optional"),
      blocking: Boolean(item.blocking),
      title: textValue(item.title, String(item.key).replaceAll("_", " ")),
    };
    let redacted = false;
    for (const targetKey of ["endpoint", "command", "docs"]) {
      if (typeof item[targetKey] === "string" && item[targetKey].trim() !== "") {
        const safeValue = safeActionTarget(item[targetKey]);
        if (safeValue === null) {
          redacted = true;
        } else {
          summary[targetKey] = safeValue;
        }
      }
    }
    if (redacted) {
      summary.target_redacted = true;
    }
    items.push(summary);
  }
  return items;
}

function actionPlanSummary({ source, status, items, planSummary }) {
  return {
    source,
    status,
    summary: actionPlanSummaryCounts(planSummary, items),
    blocking_keys: items.filter((item) => item.blocking).map((item) => String(item.key)),
    action_required_keys: items
      .filter((item) => ["action_required", "blocked"].includes(item.status))
      .map((item) => String(item.key)),
    ready_next_steps: items
      .filter((item) => item.status === "ready" && !item.blocking)
      .map((item) => String(item.key)),
    items,
  };
}

function actionPlanSummaryCounts(planSummary, items) {
  const computed = {
    total: items.length,
    blocking: items.filter((item) => item.blocking).length,
    high: items.filter((item) => item.priority === "high").length,
    medium: items.filter((item) => item.priority === "medium").length,
    low: items.filter((item) => item.priority === "low").length,
  };
  const source = asObject(planSummary);
  return Object.fromEntries(
    Object.entries(computed).map(([key, fallback]) => [key, nonNegativeInteger(source[key], fallback)]),
  );
}

function nonNegativeInteger(value, fallback) {
  if (typeof value === "boolean") {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : fallback;
}

function bundleReadinessStatus(bundle) {
  const readiness = asObject(bundle.readiness);
  const providers = asObject(readiness.providers);
  const externalApi = asObject(readiness.external_api);
  for (const value of [
    bundle.status,
    readiness.status,
    readiness.overall_status,
    providers.overall_status,
    providers.status,
    externalApi.status,
  ]) {
    const text = textValue(value, "");
    if (text) {
      return text;
    }
  }
  return "unknown";
}

function textValue(value, defaultValue) {
  return typeof value === "string" && value.trim() !== "" ? value : defaultValue;
}

function safeActionTarget(value) {
  const text = String(value || "").trim();
  if (!text) {
    return null;
  }
  return SECRET_TARGET_PATTERNS.some((pattern) => pattern.test(text)) ? null : value;
}

function buildIntegrationBundle(baseUrl, discovery) {
  const capabilities = asObject(discovery.capabilities);
  const providers = asObject(discovery.providers);
  const openapi = asObject(discovery.openapi);
  const manifest = asObject(capabilities.integration_manifest);
  const deploymentProfile = asObject(capabilities.deployment_profile || manifest.deployment);
  const selectionPolicy = asObject(capabilities.selection_policy || manifest.selection);
  const providerReadiness = asObject(providers.readiness_summary);
  const auth = asObject(manifest.auth || capabilities.auth);

  return {
    base_url: String(baseUrl || "").replace(/\/+$/, ""),
    endpoints: discovery.endpoints || capabilities.endpoints || {},
    auth: {
      header: String(auth.header || "X-API-Key"),
      placeholder: String(auth.placeholder || "<your-api-key>"),
    },
    documentation: asObject(capabilities.documentation || manifest.documentation),
    provider_selection: {
      source_priority:
        selectionPolicy.source_priority || deploymentProfile.priority || deploymentProfile.source_priority || [],
      provider_values: deploymentProfile.provider_values || selectionPolicy.provider_values || {},
      config_file: selectionPolicy.config_file || deploymentProfile.config_file || {},
    },
    templates: deploymentProfile.templates || selectionPolicy.templates || {},
    workflows: workflowSummary(manifest),
    readiness: {
      overall_status: providerReadiness.overall_status,
      totals: providerReadiness.totals || {},
      issues: providerReadiness.issues || {},
    },
    openapi: {
      version: String(openapi.openapi || ""),
      path_count: openapi.paths && typeof openapi.paths === "object" && !Array.isArray(openapi.paths)
        ? Object.keys(openapi.paths).length
        : 0,
    },
  };
}

function shouldFallbackToLocalBundle(error) {
  if (!(error instanceof MailOpsApiError)) {
    return false;
  }
  return [404, 405, 501].includes(error.status) || ["NOT_FOUND", "METHOD_NOT_ALLOWED", "NOT_IMPLEMENTED"].includes(error.code);
}

function requireText(value, name) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${name} is required`);
  }
  return value;
}

class MailOpsClient {
  constructor(baseUrl, apiKey, { timeoutSeconds = 20, transport = fetchTransport } = {}) {
    this.baseUrl = requireText(baseUrl, "baseUrl").replace(/\/+$/, "");
    this.apiKey = requireText(apiKey, "apiKey");
    this.timeoutSeconds = timeoutSeconds;
    this.transport = transport;
    this._endpoints = { ...DEFAULT_ENDPOINTS };
  }

  get endpoints() {
    return { ...this._endpoints };
  }

  async discover() {
    const capabilities = await this.get("capabilities");
    const capabilityData = dataOrPayload(capabilities);
    const endpoints = capabilityData.endpoints;
    if (endpoints && typeof endpoints === "object" && !Array.isArray(endpoints)) {
      for (const [key, value] of Object.entries(endpoints)) {
        if (value) {
          this._endpoints[String(key)] = String(value);
        }
      }
    }

    const providers = await this.get("providers");
    const openapi = await this.get("openapi");
    const documentation =
      capabilityData.documentation && typeof capabilityData.documentation === "object" && !Array.isArray(capabilityData.documentation)
        ? capabilityData.documentation
        : {};

    return {
      capabilities: capabilityData,
      providers: dataOrPayload(providers),
      openapi,
      documentation,
      endpoints: this.endpoints,
    };
  }

  async integrationBundle() {
    try {
      return dataOrPayload(await this.get("integration_bundle"));
    } catch (error) {
      if (!shouldFallbackToLocalBundle(error)) {
        throw error;
      }
      return buildIntegrationBundle(this.baseUrl, await this.discover());
    }
  }

  async get(endpointKey) {
    return this._request("GET", this._endpoint(endpointKey), null);
  }

  async post(endpointKey, body) {
    return this._request("POST", this._endpoint(endpointKey), body);
  }

  async startMailboxSession(options) {
    const callerId = options.callerId ?? options.caller_id;
    const taskId = options.taskId ?? options.task_id;
    const sourceStrategy = options.sourceStrategy ?? options.source_strategy ?? "pool_first";
    const body = withoutNil({
      caller_id: callerId,
      task_id: taskId,
      source_strategy: sourceStrategy,
      provider: options.provider,
      provider_name: options.providerName ?? options.provider_name,
      email_domain: options.emailDomain ?? options.email_domain,
      project_key: options.projectKey ?? options.project_key,
      prefix: options.prefix,
      domain: options.domain,
    });
    return dataOrPayload(await this.post("mailbox_session_start", body));
  }

  async readSession(options) {
    const callerId = options.callerId ?? options.caller_id;
    const taskId = options.taskId ?? options.task_id;
    const sessionType = options.sessionType ?? options.session_type;
    const readAction = options.readAction ?? options.read_action;
    const reserved = new Set(["callerId", "caller_id", "taskId", "task_id", "sessionType", "session_type", "readAction", "read_action"]);
    const filters = {};

    for (const [key, value] of Object.entries(options)) {
      if (reserved.has(key)) {
        continue;
      }
      if (!READ_FILTER_FIELDS.has(key)) {
        throw new Error(`unsupported read filter: ${key}`);
      }
      filters[key] = value;
    }

    const body = withoutNil({
      session_type: sessionType,
      read_action: readAction,
      caller_id: callerId,
      task_id: taskId,
      ...filters,
    });
    return dataOrPayload(await this.post("mailbox_session_read", body));
  }

  async readVerificationCode(options) {
    return this.readSession({ ...options, readAction: "verification_code", read_action: "verification_code" });
  }

  async closeSession(options) {
    const callerId = options.callerId ?? options.caller_id;
    const taskId = options.taskId ?? options.task_id;
    const sessionType = options.sessionType ?? options.session_type;
    const body = withoutNil({
      session_type: sessionType,
      caller_id: callerId,
      task_id: taskId,
      account_id: options.accountId ?? options.account_id,
      claim_token: options.claimToken ?? options.claim_token,
      task_token: options.taskToken ?? options.task_token,
      result: options.result ?? "success",
      detail: options.detail,
      reason: options.reason,
    });
    return dataOrPayload(await this.post("mailbox_session_close", body));
  }

  async verificationFlow(options) {
    const callerId = options.callerId ?? options.caller_id;
    const taskId = options.taskId ?? options.task_id;
    const sinceMinutes = options.sinceMinutes ?? options.since_minutes ?? 10;
    const closeResult = options.closeResult ?? options.close_result ?? "success";
    let session = null;
    let closeData = null;
    let verification = null;

    try {
      session = await this.startMailboxSession(options);
      verification = await this.readVerificationCode({
        session_type: String(session.session_type || session.sessionType || ""),
        caller_id: callerId,
        task_id: taskId,
        email: session.email,
        claim_token: lifecycleValue(session, "claim_token"),
        task_token: lifecycleValue(session, "task_token"),
        since_minutes: sinceMinutes,
      });
    } finally {
      if (session) {
        closeData = await this.closeSession({
          session_type: String(session.session_type || session.sessionType || ""),
          caller_id: callerId,
          task_id: taskId,
          account_id: lifecycleValue(session, "account_id"),
          claim_token: lifecycleValue(session, "claim_token"),
          task_token: lifecycleValue(session, "task_token"),
          result: closeResult,
        });
      }
    }

    return { session, verification, close: closeData };
  }

  _endpoint(key) {
    const endpoint = this._endpoints[key];
    if (!endpoint) {
      throw new Error(`unknown endpoint key: ${key}`);
    }
    return endpoint;
  }

  async _request(method, path, body) {
    const url = joinUrl(this.baseUrl, path);
    const response = await this.transport(method.toUpperCase(), url, this.apiKey, body, this.timeoutSeconds);
    const payload = response.payload;
    if (payload.success === false) {
      const code = String(payload.code || "API_ERROR");
      const message = String(payload.message || code);
      throw new MailOpsApiError(message, { status: response.status, code, payload });
    }
    return payload;
  }
}

function readFlag(argv, index) {
  const value = argv[index + 1];
  if (!value || value.startsWith("--")) {
    throw new Error(`${argv[index]} requires a value`);
  }
  return value;
}

function parseCli(argv, env) {
  const parsed = {
    baseUrl: "",
    apiKey: env.MAILOPS_API_KEY || env.OUTLOOK_EMAIL_PLUS_API_KEY || "",
    timeoutSeconds: 20,
    command: "",
    commandOptions: {},
  };
  let index = 0;

  while (index < argv.length) {
    const arg = argv[index];
    if (!arg.startsWith("--")) {
      parsed.command = arg;
      index += 1;
      break;
    }
    if (arg === "--base-url") {
      parsed.baseUrl = readFlag(argv, index);
      index += 2;
    } else if (arg === "--api-key") {
      parsed.apiKey = readFlag(argv, index);
      index += 2;
    } else if (arg === "--timeout") {
      parsed.timeoutSeconds = Number(readFlag(argv, index));
      index += 2;
    } else {
      throw new Error(`unknown option: ${arg}`);
    }
  }

  if (!parsed.baseUrl) {
    throw new Error("--base-url is required");
  }
  if (!parsed.apiKey) {
    throw new Error(
      "--api-key or MAILOPS_API_KEY is required (legacy: OUTLOOK_EMAIL_PLUS_API_KEY)",
    );
  }
  if (!parsed.command) {
    throw new Error("command is required: discover, integration-bundle, or verification-code");
  }

  while (index < argv.length) {
    const arg = argv[index];
    if (arg === "--summary") {
      parsed.commandOptions.summary = true;
      index += 1;
      continue;
    }
    const value = readFlag(argv, index);
    if (arg === "--caller-id") parsed.commandOptions.callerId = value;
    else if (arg === "--output") parsed.commandOptions.output = value;
    else if (arg === "--task-id") parsed.commandOptions.taskId = value;
    else if (arg === "--source-strategy") parsed.commandOptions.sourceStrategy = value;
    else if (arg === "--provider") parsed.commandOptions.provider = value;
    else if (arg === "--provider-name") parsed.commandOptions.providerName = value;
    else if (arg === "--email-domain") parsed.commandOptions.emailDomain = value;
    else if (arg === "--project-key") parsed.commandOptions.projectKey = value;
    else if (arg === "--prefix") parsed.commandOptions.prefix = value;
    else if (arg === "--domain") parsed.commandOptions.domain = value;
    else if (arg === "--since-minutes") parsed.commandOptions.sinceMinutes = Number(value);
    else if (arg === "--result") parsed.commandOptions.closeResult = value;
    else throw new Error(`unknown option: ${arg}`);
    index += 2;
  }

  return parsed;
}

function buildClient(baseUrl, apiKey, options, clientFactory) {
  if (clientFactory) {
    return clientFactory(baseUrl, apiKey, options);
  }
  return new MailOpsClient(baseUrl, apiKey, options);
}

async function main(argv = process.argv.slice(2), { env = process.env, stdout = console.log, stderr = console.error, clientFactory = null } = {}) {
  let parsed;
  try {
    parsed = parseCli(argv, env);
  } catch (error) {
    stderr(error.message);
    return 2;
  }

  const client = buildClient(parsed.baseUrl, parsed.apiKey, { timeoutSeconds: parsed.timeoutSeconds }, clientFactory);
  try {
    if (parsed.command === "discover") {
      stdout(compactJson(await client.discover()));
      return 0;
    }
    if (parsed.command === "integration-bundle") {
      const bundle = await client.integrationBundle();
      const payload = parsed.commandOptions.summary ? summarizeIntegrationBundleActionPlan(bundle) : bundle;
      const serialized = `${compactJson(payload)}\n`;
      if (parsed.commandOptions.output) {
        const outputPath = String(parsed.commandOptions.output);
        fs.mkdirSync(path.dirname(outputPath), { recursive: true });
        fs.writeFileSync(outputPath, serialized, "utf8");
        stdout(outputPath);
        return 0;
      }
      stdout(serialized.trimEnd());
      return 0;
    }
    if (parsed.command === "verification-code") {
      if (!parsed.commandOptions.callerId || !parsed.commandOptions.taskId) {
        stderr("verification-code requires --caller-id and --task-id");
        return 2;
      }
      stdout(compactJson(await client.verificationFlow(parsed.commandOptions)));
      return 0;
    }
    stderr(`unsupported command: ${parsed.command}`);
    return 2;
  } catch (error) {
    if (error instanceof MailOpsApiError) {
      stderr(`External API error: ${error.message}`);
      if (error.payload && Object.keys(error.payload).length > 0) {
        stderr(compactJson(error.payload));
      }
      return 2;
    }
    throw error;
  }
}

module.exports = {
  buildIntegrationBundle,
  CANONICAL_EXTERNAL_PREFIX,
  DEFAULT_ENDPOINTS,
  MailOpsApiError,
  MailOpsClient,
  main,
  summarizeIntegrationBundleActionPlan,
};

if (require.main === module) {
  main().then((exitCode) => {
    process.exitCode = exitCode;
  });
}
