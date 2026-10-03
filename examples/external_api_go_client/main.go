// MailOps external API starter client (Go, standard library only).
//
// Mirrors examples/external_api_python_client.py: discovery, the unified
// mailbox session workflow, verification-code extraction, and lifecycle close.
//
// Usage:
//
//	export MAILOPS_BASE_URL=http://127.0.0.1:5001
//	export MAILOPS_API_KEY=<your-api-key>
//	go run main.go discover
//	go run main.go verification-code -caller registry-1 -task job-42
//
// The verification-code subcommand starts a mailbox session, polls the latest
// verification code once, and closes the session with result=success.
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

const canonicalExternalPrefix = "/api/v1/external"

var defaultEndpoints = map[string]string{
	"capabilities":          canonicalExternalPrefix + "/capabilities",
	"integration_bundle":    canonicalExternalPrefix + "/integration-bundle",
	"providers":             canonicalExternalPrefix + "/providers",
	"docs":                  canonicalExternalPrefix + "/docs",
	"openapi":               canonicalExternalPrefix + "/openapi.json",
	"mailbox_session_start": canonicalExternalPrefix + "/mailbox-sessions/start",
	"mailbox_session_read":  canonicalExternalPrefix + "/mailbox-sessions/read",
	"mailbox_session_close": canonicalExternalPrefix + "/mailbox-sessions/close",
}

// APIError carries the structured error envelope the external API returns
// ({success:false, code, message, data}).
type APIError struct {
	Code    string         `json:"code"`
	Message string         `json:"message"`
	Status  int            `json:"-"`
	Payload map[string]any `json:"-"`
}

func (e *APIError) Error() string {
	return fmt.Sprintf("external api error %s (http %d): %s", e.Code, e.Status, e.Message)
}

// Client is a minimal MailOps external API client.
type Client struct {
	baseURL   string
	apiKey    string
	http      *http.Client
	endpoints map[string]string
}

// NewClient builds a client from environment configuration.
// MAILOPS_BASE_URL defaults to http://127.0.0.1:5001 and MAILOPS_API_KEY must
// be set (create one in Settings -> API Security, or via the API).
func NewClient() (*Client, error) {
	baseURL := strings.TrimRight(os.Getenv("MAILOPS_BASE_URL"), "/")
	if baseURL == "" {
		baseURL = "http://127.0.0.1:5001"
	}
	apiKey := os.Getenv("MAILOPS_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("MAILOPS_API_KEY is required")
	}
	endpoints := make(map[string]string, len(defaultEndpoints))
	for key, path := range defaultEndpoints {
		endpoints[key] = baseURL + path
	}
	return &Client{
		baseURL:   baseURL,
		apiKey:    apiKey,
		http:      &http.Client{Timeout: 30 * time.Second},
		endpoints: endpoints,
	}, nil
}

func (c *Client) do(method, endpointKey string, body map[string]any) (map[string]any, error) {
	endpoint, ok := c.endpoints[endpointKey]
	if !ok {
		return nil, fmt.Errorf("unknown endpoint key: %s", endpointKey)
	}
	var reader io.Reader
	if body != nil {
		encoded, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reader = bytes.NewReader(encoded)
	}
	req, err := http.NewRequest(method, endpoint, reader)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-API-Key", c.apiKey)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("non-json response (http %d): %.200s", resp.StatusCode, string(raw))
	}
	if success, ok := payload["success"].(bool); ok && !success {
		code, _ := payload["code"].(string)
		message, _ := payload["message"].(string)
		return nil, &APIError{Code: code, Message: message, Status: resp.StatusCode, Payload: payload}
	}
	return payload, nil
}

// data unwraps the {success, data} envelope into the inner object.
func data(payload map[string]any) map[string]any {
	if inner, ok := payload["data"].(map[string]any); ok {
		return inner
	}
	return payload
}

func (c *Client) get(endpointKey string) (map[string]any, error) {
	return c.do(http.MethodGet, endpointKey, nil)
}

// Discover returns the readiness contracts: capabilities, providers, and the
// OpenAPI document. It also adopts any endpoints the server advertises.
func (c *Client) Discover() (map[string]any, error) {
	capabilitiesPayload, err := c.get("capabilities")
	if err != nil {
		return nil, err
	}
	capabilities := data(capabilitiesPayload)
	if endpoints, ok := capabilities["endpoints"].(map[string]any); ok {
		for key, value := range endpoints {
			if path, ok := value.(string); ok && path != "" {
				if _, known := defaultEndpoints[key]; known {
					c.endpoints[key] = c.baseURL + path
				}
			}
		}
	}
	providersPayload, err := c.get("providers")
	if err != nil {
		return nil, err
	}
	openapiPayload, err := c.get("openapi")
	if err != nil {
		return nil, err
	}
	return map[string]any{
		"capabilities": capabilities,
		"providers":    data(providersPayload),
		"openapi":      data(openapiPayload),
	}, nil
}

// SessionOptions selects where the mailbox comes from and how it is claimed.
// Empty fields are omitted from the request body (omitempty).
type SessionOptions struct {
	CallerID       string `json:"caller_id"`
	TaskID         string `json:"task_id"`
	SourceStrategy string `json:"source_strategy,omitempty"`
	Provider       string `json:"provider,omitempty"`
	ProviderName   string `json:"provider_name,omitempty"`
	EmailDomain    string `json:"email_domain,omitempty"`
	ProjectKey     string `json:"project_key,omitempty"`
	Prefix         string `json:"prefix,omitempty"`
	Domain         string `json:"domain,omitempty"`
}

// StartMailboxSession claims a mailbox and returns {session_type, email, ...}.
func (c *Client) StartMailboxSession(opts SessionOptions) (map[string]any, error) {
	if opts.SourceStrategy == "" {
		opts.SourceStrategy = "pool_first"
	}
	payload, err := c.do(http.MethodPost, "mailbox_session_start", toMap(opts))
	if err != nil {
		return nil, err
	}
	return data(payload), nil
}

// ReadFilter narrows a session read. Only canonical filter fields are allowed.
type ReadFilter struct {
	Email        string `json:"email,omitempty"`
	ClaimToken   string `json:"claim_token,omitempty"`
	TaskToken    string `json:"task_token,omitempty"`
	MessageID    string `json:"message_id,omitempty"`
	SinceMinutes int    `json:"since_minutes,omitempty"`
}

var readFilterFields = map[string]bool{
	"email": true, "claim_token": true, "task_token": true,
	"message_id": true, "since_minutes": true,
}

// ReadSession performs one read_action (verification_code/latest/detail/probe).
func (c *Client) ReadSession(sessionType, readAction string, opts SessionOptions, filter ReadFilter) (map[string]any, error) {
	body := toMap(opts)
	body["session_type"] = sessionType
	body["read_action"] = readAction
	extra, err := json.Marshal(filter)
	if err != nil {
		return nil, err
	}
	var filterMap map[string]any
	if err := json.Unmarshal(extra, &filterMap); err != nil {
		return nil, err
	}
	for key, value := range filterMap {
		if !readFilterFields[key] {
			return nil, fmt.Errorf("unsupported read filter: %s", key)
		}
		if value != nil {
			body[key] = value
		}
	}
	payload, err := c.do(http.MethodPost, "mailbox_session_read", body)
	if err != nil {
		return nil, err
	}
	return data(payload), nil
}

// CloseSession ends the lifecycle. result=success (default) releases the
// mailbox back to the pool when project-scoped reuse applies.
func (c *Client) CloseSession(sessionType, callerID, taskID string, claimToken, taskToken, result string, accountID int64) (map[string]any, error) {
	if result == "" {
		result = "success"
	}
	body := map[string]any{
		"session_type": sessionType,
		"caller_id":    callerID,
		"task_id":      taskID,
		"result":       result,
	}
	if accountID != 0 {
		body["account_id"] = accountID
	}
	if claimToken != "" {
		body["claim_token"] = claimToken
	}
	if taskToken != "" {
		body["task_token"] = taskToken
	}
	payload, err := c.do(http.MethodPost, "mailbox_session_close", body)
	if err != nil {
		return nil, err
	}
	return data(payload), nil
}

// VerificationFlow runs the canonical end-to-end loop: start a session, read
// the latest verification code, close with success, and always close on error
// paths with result=release so the mailbox is not stuck in claimed state.
func (c *Client) VerificationFlow(opts SessionOptions) (map[string]any, error) {
	session, err := c.StartMailboxSession(opts)
	if err != nil {
		return nil, err
	}
	sessionType, _ := session["session_type"].(string)
	lifecycle, _ := session["lifecycle"].(map[string]any)
	claimToken, _ := lifecycle["claim_token"].(string)
	accountID, _ := lifecycle["account_id"].(float64)
	// task mailboxes carry the token at the top level instead of lifecycle
	taskToken, _ := session["task_token"].(string)
	if taskToken == "" {
		if fromLifecycle, ok := lifecycle["task_token"].(string); ok {
			taskToken = fromLifecycle
		}
	}

	result := map[string]any{"session": session}
	// Mirror the Python starter client: reads are scoped by the claimed
	// mailbox (email) and the lifecycle tokens from the session.
	email, _ := session["email"].(string)
	filter := ReadFilter{SinceMinutes: 10, Email: email, ClaimToken: claimToken, TaskToken: taskToken}
	verification, readErr := c.ReadSession(sessionType, "verification_code", opts, filter)
	if readErr != nil {
		result["verification_error"] = readErr.Error()
	} else {
		result["verification"] = verification
	}

	closeResult := "success"
	if readErr != nil {
		closeResult = "release"
	}
	closeData, closeErr := c.CloseSession(sessionType, opts.CallerID, opts.TaskID, claimToken, taskToken, closeResult, int64(accountID))
	if closeErr != nil {
		result["close_error"] = closeErr.Error()
	} else {
		result["close"] = closeData
	}
	if readErr != nil {
		return result, readErr
	}
	return result, nil
}

func toMap(value any) map[string]any {
	encoded, err := json.Marshal(value)
	if err != nil {
		panic(err) // impossible for struct tags used here
	}
	var out map[string]any
	if err := json.Unmarshal(encoded, &out); err != nil {
		panic(err)
	}
	return out
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: go run main.go <discover|verification-code> [-caller id] [-task id] [-provider key]")
		os.Exit(2)
	}
	command := os.Args[1]
	fs := flag.NewFlagSet(command, flag.ExitOnError)
	caller := fs.String("caller", "go-worker-1", "caller_id for pool claiming and audit")
	task := fs.String("task", fmt.Sprintf("go-job-%d", time.Now().Unix()), "task_id for this run")
	provider := fs.String("provider", "", "explicit provider key (optional)")
	strategy := fs.String("strategy", "pool_first", "source strategy: pool_first | task_temp_first | pool_only | task_temp_only")
	fs.Parse(os.Args[2:])

	client, err := NewClient()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}

	switch command {
	case "discover":
		result, err := client.Discover()
		if err != nil {
			exitWithError(err)
		}
		printJSON(result)
	case "verification-code":
		result, err := client.VerificationFlow(SessionOptions{
			CallerID:       *caller,
			TaskID:         *task,
			Provider:       *provider,
			SourceStrategy: *strategy,
		})
		if err != nil {
			printJSON(result)
			exitWithError(err)
		}
		printJSON(result)
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s (expected discover or verification-code)\n", command)
		os.Exit(2)
	}
}

func printJSON(value map[string]any) {
	if value == nil {
		value = map[string]any{}
	}
	encoded, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(string(encoded))
}

func exitWithError(err error) {
	if apiErr, ok := err.(*APIError); ok {
		fmt.Fprintf(os.Stderr, "external api error: %s %s\n", apiErr.Code, apiErr.Message)
	} else if urlErr, ok := err.(*url.Error); ok {
		fmt.Fprintf(os.Stderr, "transport error: %v\n", urlErr)
	} else {
		fmt.Fprintln(os.Stderr, err)
	}
	os.Exit(1)
}
