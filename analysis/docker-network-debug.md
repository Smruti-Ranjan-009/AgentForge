# Docker Network Debug — Benchmark Analysis

## Objective

This benchmark evaluates whether a developer can diagnose and repair a real container-to-container connectivity failure. It tests investigation, Docker networking, service discovery, and runtime configuration through observable behavior rather than a configuration-text assertion.

## Environment

```text
Client/debug container
         |
         | isolated Docker network
         v
    Backend container
```

The client and backend run as separate containers on an isolated, AgentForge-managed Docker network. Docker DNS makes the backend available to the client by its service name.

## Initial State

```env
BACKEND_URL=http://localhost:8000
```

This URL directs the client to port 8000 inside its own container. The backend listens on port 8000 in a different container, so no service is listening at the client's loopback address.

## Investigation

The manual debugging run used the following commands:

```sh
cat instruction.md
cat config.env
getent hosts backend
curl -v http://localhost:8000
curl -v http://backend:8000
bash tests/test.sh
```

- `cat instruction.md` establishes the reported symptom and the constraint not to change tests.
- `cat config.env` exposes the runtime endpoint initially configured as `localhost`.
- `getent hosts backend` confirms that Docker DNS resolves `backend` to an address on the task network (observed as `172.18.0.2`).
- `curl -v http://localhost:8000` shows the request reaches the client's own loopback interface and is refused.
- `curl -v http://backend:8000` shows a successful connection to the separate backend and its deterministic response, `AgentForge backend is healthy.`
- `bash tests/test.sh` verifies the configured URL with a real HTTP request.

## Root Cause

`localhost` always refers to the network namespace of the process making the request. Since the request originates in the client container, `localhost` identifies that client, not the backend container. The backend is reachable through Docker's network DNS name.

## Fix

Set the runtime endpoint to the backend service name:

```env
BACKEND_URL=http://backend:8000
```

The reference solution changes only `config.env`. Modifying the test would hide the connectivity defect rather than fix it.

## Behavioral Verification

```text
broken configuration -> HTTP test fails
corrected Docker hostname -> HTTP test passes
```

The test performs a real request and checks the deterministic backend response. The grader uses the same persistent client, backend, and network as the interactive debugging session.

## Why This Benchmark Is Useful

It exercises Linux/CLI investigation, Docker container isolation, Docker DNS, service discovery, runtime configuration, network debugging, and behavior-based verification in one reproducible task.

## Anticipated Failure Modes

These are general hypotheses, not observed results from a coding-agent attempt:

- changing host port mappings unnecessarily
- assuming `localhost` means the host machine
- modifying tests instead of application configuration
- attempting to expose the backend publicly
- failing to inspect Docker DNS
- confusing host networking with container networking

## Benchmark Quality Review

The initial failure is deterministic, the environment is reproducible, the requested outcome is minimally ambiguous, and grading is based on a real HTTP response. A reference solution is provided, resources are isolated and labeled, and cleanup removes the managed containers and network. The task requires no external APIs or cloud services.

The root cause becomes fairly direct once Docker DNS is inspected, and this benchmark evaluates one networking failure rather than a multi-fault incident. A harder future version could combine DNS, health checks, startup order, and configuration propagation.

## Evaluation Lifecycle

```text
Broken environment
        ↓
Investigation
        ↓
Configuration fix
        ↓
Automated behavioral test
        ↓
Grade
        ↓
Report
        ↓
Cleanup
```
