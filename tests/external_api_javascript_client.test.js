"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");

const {
  buildIntegrationBundle,
  CANONICAL_EXTERNAL_PREFIX,
  MailOpsApiError,
  MailOpsClient,
  main,
  summarizeIntegrationBundleActionPlan,
} = require("../examples/external_api_javascript_client");

function url(path) {
  return `https://mailbox.example.test${path}`;
}

function ok(data) {
  return { success: true, code: "OK", message: "success", data };
}

function discoveryResponses() {
  const endpoints = {
    capabilities: `${CANONICAL_EXTERNAL_PREFIX}/capabilities`,
    integration_bundle: `${CANONICAL_EXTERNAL_PREFIX}/integration-bundle`,
    providers: `${CANONICAL_EXTERNAL_PREFIX}/providers`,
    docs: `${CANONICAL_EXTERNAL_PREFIX}/docs`,
    openapi: `${CANONICAL_EXTERNAL_PREFIX}/openapi.json`,
    mailbox_session_start: `${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start`,
    mailbox_session_read: `${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read`,
    mailbox_session_close: `${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close`,
  };
  return new Map([
    [
      `GET ${url(endpoints.capabilities)}`,
      ok({
        endpoints,
        documentation: { entries: { api_docs: { endpoint: endpoints.docs } } },
        integration_manifest: {
          auth: { header: "X-API-Key", placeholder: "<your-api-key>" },
          workflows: [
            {
              key: "start_mailbox_session",
              label: "Start mailbox session",
              description: "Create a provider-neutral mailbox session.",
            },
            { key: "browse_mailbox_directory", label: "Browse mailbox directory" },
          ],
        },
        deployment_profile: {
          provider_values: {
            temp_apply: ["mail_tm", "duckmail"],
            pool_claim: ["auto", "imap", "mail_tm"],
          },
          templates: {
            env: {
              format: "env",
              content: "TEMP_MAIL_PROVIDER=mail_tm\nDUCKMAIL_BEARER_TOKEN=\n",
            },
            provider_config_json: {
              format: "json",
              content: "{\n  \"providers\": {\n    \"temp_mail_provider\": \"mail_tm\"\n  }\n}\n",
            },
          },
          config_file: { priority_slot: "provider_config_file" },
        },
        selection_policy: { source_priority: ["env", "provider_config_file", "settings", "default"] },
      }),
    ],
    [`GET ${url(endpoints.integration_bundle)}`, ok(liveIntegrationBundleData())],
    [
      `GET ${url(endpoints.providers)}`,
      ok({
        providers: [],
        readiness_summary: {
          overall_status: "ready",
          totals: { providers: 2, ready_providers: 2 },
          issues: { needs_config: 0 },
        },
      }),
    ],
    [`GET ${url(endpoints.openapi)}`, { openapi: "3.1.0", paths: { "/api/v1/external/capabilities": {} } }],
  ]);
}

function liveIntegrationBundleData() {
  return {
    version: 1,
    service: "mailops",
    status: "ready",
    auth: { header: "X-API-Key", placeholder: "<your-api-key>" },
    endpoints: {
      integration_bundle: `${CANONICAL_EXTERNAL_PREFIX}/integration-bundle`,
      openapi: `${CANONICAL_EXTERNAL_PREFIX}/openapi.json`,
    },
    readiness: {
      providers: {
        overall_status: "ready",
        totals: { providers: 2, ready_providers: 2 },
        issues: { needs_config: 0 },
      },
    },
    openapi: { version: "3.1.0", path_count: 2 },
    action_plan: {
      version: 1,
      status: "ready",
      summary: { total: 2, blocking: 0, high: 1, medium: 1, low: 0 },
      items: [
        {
          key: "run_smoke_check",
          priority: "high",
          status: "ready",
          blocking: false,
          title: "Run smoke checker",
          command:
            "MAILOPS_API_KEY=<your-api-key> python scripts/external_api_smoke.py --base-url <your-base-url>",
        },
        {
          key: "start_mailbox_session",
          priority: "medium",
          status: "ready",
          blocking: false,
          title: "Start mailbox session",
          endpoint: `${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start`,
        },
      ],
    },
  };
}

function makeTransport(responses, { failOn = null, failStatus = 500, failCode = "READ_FAILED" } = {}) {
  const calls = [];
  const transport = async (method, requestUrl, apiKey, body, timeoutSeconds) => {
    calls.push({ method, url: requestUrl, apiKey, body, timeoutSeconds });
    const key = `${method} ${requestUrl}`;
    if (failOn === key) {
      throw new MailOpsApiError("read failed", {
        status: failStatus,
        code: failCode,
        payload: { success: false, code: failCode },
      });
    }
    if (!responses.has(key)) {
      throw new Error(`missing fake response for ${key}`);
    }
    return { status: 200, payload: responses.get(key) };
  };
  transport.calls = calls;
  return transport;
}

test("discover reads canonical endpoints and caches endpoint map", async () => {
  const transport = makeTransport(discoveryResponses());
  const client = new MailOpsClient("https://mailbox.example.test", "test-key", { transport });

  const data = await client.discover();

  assert.equal(data.endpoints.mailbox_session_read, `${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read`);
  assert.equal(client.endpoints.docs, `${CANONICAL_EXTERNAL_PREFIX}/docs`);
  assert.deepEqual(
    transport.calls.map((call) => call.url),
    [
      url(`${CANONICAL_EXTERNAL_PREFIX}/capabilities`),
      url(`${CANONICAL_EXTERNAL_PREFIX}/providers`),
      url(`${CANONICAL_EXTERNAL_PREFIX}/openapi.json`),
    ],
  );
});

test("start, read, and close use session endpoints and expected bodies", async () => {
  const responses = discoveryResponses();
  responses.set(
    `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start`)}`,
    ok({
      session_type: "pool_claim",
      email: "user@example.test",
      lifecycle: { account_id: 7, claim_token: "claim-demo" },
    }),
  );
  responses.set(
    `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read`)}`,
    ok({ session_type: "pool_claim", read_action: "verification_code", result: { verification_code: "123456" } }),
  );
  responses.set(
    `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close`)}`,
    ok({ session_type: "pool_claim", status: "closed" }),
  );
  const transport = makeTransport(responses);
  const client = new MailOpsClient("https://mailbox.example.test", "test-key", { transport });
  await client.discover();

  const result = await client.verificationFlow({
    callerId: "registration-worker-1",
    taskId: "signup-demo-1",
    provider: "auto",
    providerName: "mail_tm",
  });

  assert.equal(result.verification.result.verification_code, "123456");
  assert.equal(result.close.status, "closed");
  const postBodies = transport.calls.filter((call) => call.method === "POST").map((call) => call.body);
  assert.equal(postBodies[0].source_strategy, "pool_first");
  assert.equal(postBodies[0].provider, "auto");
  assert.equal(postBodies[0].provider_name, "mail_tm");
  assert.equal(postBodies[1].read_action, "verification_code");
  assert.equal(postBodies[1].claim_token, "claim-demo");
  assert.equal(postBodies[2].account_id, 7);
  assert.equal(postBodies[2].claim_token, "claim-demo");
});

test("start uses canonical fallback without discovery", async () => {
  const responses = new Map([
    [
      `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start`)}`,
      ok({ session_type: "task_temp_mailbox", email: "temp@example.test", lifecycle: { task_token: "task-demo" } }),
    ],
  ]);
  const transport = makeTransport(responses);
  const client = new MailOpsClient("https://mailbox.example.test", "test-key", { transport });

  const session = await client.startMailboxSession({ callerId: "worker", taskId: "task", sourceStrategy: "task_temp_only" });

  assert.equal(session.session_type, "task_temp_mailbox");
  assert.equal(transport.calls[0].url, url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start`));
});

test("verification flow closes started session when read fails", async () => {
  const responses = discoveryResponses();
  responses.set(
    `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start`)}`,
    ok({ session_type: "task_temp_mailbox", email: "temp@example.test", lifecycle: { task_token: "task-demo" } }),
  );
  responses.set(
    `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close`)}`,
    ok({ session_type: "task_temp_mailbox", status: "closed" }),
  );
  const failOn = `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read`)}`;
  const transport = makeTransport(responses, { failOn });
  const client = new MailOpsClient("https://mailbox.example.test", "test-key", { transport });
  await client.discover();

  await assert.rejects(
    () => client.verificationFlow({ callerId: "worker", taskId: "task", sourceStrategy: "task_temp_only" }),
    MailOpsApiError,
  );

  const closeCalls = transport.calls.filter((call) => call.url.endsWith("/mailbox-sessions/close"));
  assert.equal(closeCalls.length, 1);
  assert.equal(closeCalls[0].body.task_token, "task-demo");
});

test("envelope failure raises API error", async () => {
  const responses = new Map([
    [`GET ${url(`${CANONICAL_EXTERNAL_PREFIX}/capabilities`)}`, { success: false, code: "FORBIDDEN", message: "forbidden" }],
  ]);
  const client = new MailOpsClient("https://mailbox.example.test", "test-key", {
    transport: makeTransport(responses),
  });

  await assert.rejects(async () => client.get("capabilities"), (error) => {
    assert.equal(error.code, "FORBIDDEN");
    assert.equal(error.status, 200);
    return true;
  });
});

test("unsupported read filters are rejected before request", async () => {
  const transport = makeTransport(new Map());
  const client = new MailOpsClient("https://mailbox.example.test", "test-key", { transport });

  await assert.rejects(
    () =>
      client.readSession({
        sessionType: "pool_claim",
        readAction: "verification_code",
        callerId: "worker",
        taskId: "task",
        unsupported_filter: "x",
      }),
    /unsupported read filter/,
  );
  assert.equal(transport.calls.length, 0);
});

test("CLI discover uses API key from environment", async () => {
  const transport = makeTransport(discoveryResponses());

  const exitCode = await main(["--base-url", "https://mailbox.example.test", "discover"], {
    env: { MAILOPS_API_KEY: "env-key" },
    stdout: () => {},
    stderr: () => {},
    clientFactory: (baseUrl, apiKey, options) => new MailOpsClient(baseUrl, apiKey, { ...options, transport }),
  });

  assert.equal(exitCode, 0);
  assert.ok(transport.calls.every((call) => call.apiKey === "env-key"));
  assert.ok(transport.calls.every((call) => call.method === "GET"));
});

test("buildIntegrationBundle summarizes live discovery without secrets", async () => {
  const transport = makeTransport(discoveryResponses());
  const client = new MailOpsClient("https://mailbox.example.test", "test-key", { transport });

  const bundle = buildIntegrationBundle("https://mailbox.example.test/", await client.discover());
  const serialized = JSON.stringify(bundle);

  assert.equal(bundle.base_url, "https://mailbox.example.test");
  assert.deepEqual(bundle.auth, { header: "X-API-Key", placeholder: "<your-api-key>" });
  assert.equal(bundle.endpoints.mailbox_session_start, `${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start`);
  assert.equal(bundle.documentation.entries.api_docs.endpoint, `${CANONICAL_EXTERNAL_PREFIX}/docs`);
  assert.deepEqual(bundle.provider_selection.source_priority, ["env", "provider_config_file", "settings", "default"]);
  assert.ok(bundle.provider_selection.provider_values.temp_apply.includes("duckmail"));
  assert.ok(Object.hasOwn(bundle.templates, "provider_config_json"));
  assert.equal(bundle.workflows[0].key, "start_mailbox_session");
  assert.equal(bundle.readiness.overall_status, "ready");
  assert.deepEqual(bundle.openapi, { version: "3.1.0", path_count: 1 });
  assert.doesNotMatch(serialized, /test-key/);
  assert.doesNotMatch(serialized, /dk_[0-9a-fA-F]{20,}/);
});

test("CLI integration-bundle outputs JSON and uses only readonly discovery", async () => {
  const transport = makeTransport(discoveryResponses());
  let stdoutText = "";

  const exitCode = await main(["--base-url", "https://mailbox.example.test", "--api-key", "test-key", "integration-bundle"], {
    env: {},
    stdout: (text) => {
      stdoutText += text;
    },
    stderr: () => {},
    clientFactory: (baseUrl, apiKey, options) => new MailOpsClient(baseUrl, apiKey, { ...options, transport }),
  });

  const bundle = JSON.parse(stdoutText);
  const serialized = JSON.stringify(bundle);
  assert.equal(exitCode, 0);
  assert.equal(bundle.auth.placeholder, "<your-api-key>");
  assert.equal(bundle.readiness.providers.totals.providers, 2);
  assert.doesNotMatch(serialized, /test-key/);
  assert.deepEqual(
    transport.calls.map((call) => call.method),
    ["GET"],
  );
  assert.deepEqual(
    transport.calls.map((call) => call.url),
    [url(`${CANONICAL_EXTERNAL_PREFIX}/integration-bundle`)],
  );
  assert.ok(transport.calls.every((call) => !call.url.includes("mailbox-sessions")));
});

test("action plan summary projects live bundle next steps", () => {
  const summary = summarizeIntegrationBundleActionPlan(liveIntegrationBundleData());
  const serialized = JSON.stringify(summary);

  assert.equal(summary.source, "action_plan");
  assert.equal(summary.status, "ready");
  assert.deepEqual(summary.summary, { total: 2, blocking: 0, high: 1, medium: 1, low: 0 });
  assert.deepEqual(summary.blocking_keys, []);
  assert.deepEqual(summary.action_required_keys, []);
  assert.deepEqual(summary.ready_next_steps, ["run_smoke_check", "start_mailbox_session"]);
  assert.match(serialized, /<your-api-key>/);
  assert.doesNotMatch(serialized, /test-key/);
  assert.doesNotMatch(serialized, /dk_[0-9a-fA-F]{20,}/);
});

test("action plan summary redacts secret-like action targets", () => {
  const bundle = liveIntegrationBundleData();
  bundle.action_plan.items[0].command = "curl -H 'Authorization: Bearer abcdefghijklmnopqrstuvwx'";

  const summary = summarizeIntegrationBundleActionPlan(bundle);
  const serialized = JSON.stringify(summary);

  assert.equal(summary.items[0].target_redacted, true);
  assert.doesNotMatch(serialized, /abcdefghijklmnopqrstuvwx/);
  assert.doesNotMatch(serialized, /Authorization: Bearer/);
});

test("CLI integration-bundle summary outputs action plan projection", async () => {
  const transport = makeTransport(discoveryResponses());
  let stdoutText = "";

  const exitCode = await main(
    ["--base-url", "https://mailbox.example.test", "--api-key", "test-key", "integration-bundle", "--summary"],
    {
      env: {},
      stdout: (text) => {
        stdoutText += text;
      },
      stderr: () => {},
      clientFactory: (baseUrl, apiKey, options) => new MailOpsClient(baseUrl, apiKey, { ...options, transport }),
    },
  );

  const summary = JSON.parse(stdoutText);
  const serialized = JSON.stringify(summary);
  assert.equal(exitCode, 0);
  assert.equal(summary.source, "action_plan");
  assert.deepEqual(summary.ready_next_steps, ["run_smoke_check", "start_mailbox_session"]);
  assert.doesNotMatch(serialized, /test-key/);
  assert.deepEqual(
    transport.calls.map((call) => call.method),
    ["GET"],
  );
  assert.deepEqual(
    transport.calls.map((call) => call.url),
    [url(`${CANONICAL_EXTERNAL_PREFIX}/integration-bundle`)],
  );
  assert.ok(transport.calls.every((call) => !call.url.includes("mailbox-sessions")));
});

test("CLI integration-bundle falls back to local discovery for older service", async () => {
  const responses = discoveryResponses();
  const failOn = `GET ${url(`${CANONICAL_EXTERNAL_PREFIX}/integration-bundle`)}`;
  const transport = makeTransport(responses, { failOn, failStatus: 404, failCode: "NOT_FOUND" });
  let stdoutText = "";

  const exitCode = await main(["--base-url", "https://mailbox.example.test", "--api-key", "test-key", "integration-bundle"], {
    env: {},
    stdout: (text) => {
      stdoutText += text;
    },
    stderr: () => {},
    clientFactory: (baseUrl, apiKey, options) => new MailOpsClient(baseUrl, apiKey, { ...options, transport }),
  });

  const bundle = JSON.parse(stdoutText);
  assert.equal(exitCode, 0);
  assert.equal(bundle.base_url, "https://mailbox.example.test");
  assert.equal(bundle.readiness.totals.providers, 2);
  assert.deepEqual(
    transport.calls.map((call) => call.url),
    [
      url(`${CANONICAL_EXTERNAL_PREFIX}/integration-bundle`),
      url(`${CANONICAL_EXTERNAL_PREFIX}/capabilities`),
      url(`${CANONICAL_EXTERNAL_PREFIX}/providers`),
      url(`${CANONICAL_EXTERNAL_PREFIX}/openapi.json`),
    ],
  );
});

test("action plan summary handles older service fallback bundle", async () => {
  const failOn = `GET ${url(`${CANONICAL_EXTERNAL_PREFIX}/integration-bundle`)}`;
  const transport = makeTransport(discoveryResponses(), { failOn, failStatus: 404, failCode: "NOT_FOUND" });
  const client = new MailOpsClient("https://mailbox.example.test", "test-key", { transport });

  const summary = summarizeIntegrationBundleActionPlan(await client.integrationBundle());

  assert.equal(summary.source, "fallback_readiness");
  assert.equal(summary.status, "ready");
  assert.deepEqual(summary.blocking_keys, []);
  assert.ok(summary.ready_next_steps.includes("start_mailbox_session"));
});

test("CLI integration-bundle summary can write output file", async () => {
  const transport = makeTransport(discoveryResponses());
  const outputPath = "output/test-js-integration-summary/mailops.summary.json";
  fs.rmSync("output/test-js-integration-summary", { recursive: true, force: true });
  let stdoutText = "";

  try {
    const exitCode = await main(
      [
        "--base-url",
        "https://mailbox.example.test",
        "--api-key",
        "test-key",
        "integration-bundle",
        "--summary",
        "--output",
        outputPath,
      ],
      {
        env: {},
        stdout: (text) => {
          stdoutText += text;
        },
        stderr: () => {},
        clientFactory: (baseUrl, apiKey, options) => new MailOpsClient(baseUrl, apiKey, { ...options, transport }),
      },
    );

    assert.equal(exitCode, 0);
    assert.equal(stdoutText, outputPath);
    const summary = JSON.parse(fs.readFileSync(outputPath, "utf8"));
    assert.equal(summary.source, "action_plan");
    assert.equal(summary.summary.high, 1);
    assert.deepEqual(
      transport.calls.map((call) => call.method),
      ["GET"],
    );
  } finally {
    fs.rmSync("output/test-js-integration-summary", { recursive: true, force: true });
  }
});

test("CLI integration-bundle can write output file", async () => {
  const transport = makeTransport(discoveryResponses());
  const outputPath = "output/test-js-integration-bundle/mailops.integration.json";
  fs.rmSync("output/test-js-integration-bundle", { recursive: true, force: true });
  let stdoutText = "";

  try {
    const exitCode = await main(
      [
        "--base-url",
        "https://mailbox.example.test",
        "--api-key",
        "test-key",
        "integration-bundle",
        "--output",
        outputPath,
      ],
      {
        env: {},
        stdout: (text) => {
          stdoutText += text;
        },
        stderr: () => {},
        clientFactory: (baseUrl, apiKey, options) => new MailOpsClient(baseUrl, apiKey, { ...options, transport }),
      },
    );

    assert.equal(exitCode, 0);
    assert.equal(stdoutText, outputPath);
    const bundle = JSON.parse(fs.readFileSync(outputPath, "utf8"));
    assert.equal(bundle.endpoints.openapi, `${CANONICAL_EXTERNAL_PREFIX}/openapi.json`);
    assert.deepEqual(
      transport.calls.map((call) => call.method),
      ["GET"],
    );
  } finally {
    fs.rmSync("output/test-js-integration-bundle", { recursive: true, force: true });
  }
});

test("CLI verification-code forwards start selection fields", async () => {
  const responses = discoveryResponses();
  responses.set(
    `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/start`)}`,
    ok({ session_type: "task_temp_mailbox", email: "temp@example.test", lifecycle: { task_token: "task-demo" } }),
  );
  responses.set(
    `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/read`)}`,
    ok({ session_type: "task_temp_mailbox", read_action: "verification_code", result: { verification_code: "123456" } }),
  );
  responses.set(
    `POST ${url(`${CANONICAL_EXTERNAL_PREFIX}/mailbox-sessions/close`)}`,
    ok({ session_type: "task_temp_mailbox", status: "closed" }),
  );
  const transport = makeTransport(responses);

  const exitCode = await main(
    [
      "--base-url",
      "https://mailbox.example.test",
      "--api-key",
      "test-key",
      "verification-code",
      "--caller-id",
      "registration-worker-1",
      "--task-id",
      "signup-demo-1",
      "--source-strategy",
      "task_temp_only",
      "--provider",
      "auto",
      "--provider-name",
      "mail_tm",
      "--email-domain",
      "example.test",
      "--project-key",
      "project-a",
      "--prefix",
      "signup",
      "--domain",
      "mail.example.test",
      "--result",
      "success",
    ],
    {
      env: {},
      stdout: () => {},
      stderr: () => {},
      clientFactory: (baseUrl, apiKey, options) => new MailOpsClient(baseUrl, apiKey, { ...options, transport }),
    },
  );

  assert.equal(exitCode, 0);
  const startBody = transport.calls.find((call) => call.url.endsWith("/mailbox-sessions/start")).body;
  assert.equal(startBody.source_strategy, "task_temp_only");
  assert.equal(startBody.provider, "auto");
  assert.equal(startBody.provider_name, "mail_tm");
  assert.equal(startBody.email_domain, "example.test");
  assert.equal(startBody.project_key, "project-a");
  assert.equal(startBody.prefix, "signup");
  assert.equal(startBody.domain, "mail.example.test");
});

test("source contains only placeholder secrets", () => {
  const source = fs.readFileSync("examples/external_api_javascript_client.js", "utf8");

  assert.match(source, /MAILOPS_API_KEY/);
  assert.doesNotMatch(source, /dk_[0-9a-fA-F]{20,}/);
  assert.doesNotMatch(source, /DUCKMAIL_BEARER_TOKEN\s*=/);
  assert.doesNotMatch(source, /X-API-Key:\s+(?!<your-api-key>)[A-Za-z0-9_.-]{20,}/);
});
