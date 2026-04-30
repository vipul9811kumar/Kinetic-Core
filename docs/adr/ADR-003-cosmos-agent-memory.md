# ADR-003: Cosmos DB for Agent Memory and Audit Trail

**Date:** 2025-01-15  
**Status:** Accepted  
**Deciders:** Architecture Team

## Context

Agents need to persist reasoning traces for three purposes: (1) incident replay/audit, (2) retraining data collection, (3) cross-agent context sharing within a single incident lifecycle.

## Decision

Use **Azure Cosmos DB (NoSQL API)** with three containers:
- `telemetry` — raw sensor readings, 30-day TTL
- `incidents` — incident lifecycle records, no TTL (permanent audit)
- `agent-memory` — per-agent reasoning traces per incident, no TTL

Partition key: `incident_id` for incidents/agent-memory; `device_id` for telemetry.

## Consequences

- **Positive:** Serverless tier eliminates idle cost during dev/pilot.
- **Positive:** Native Change Feed enables the warm-path processing pipeline.
- **Positive:** Multi-region replication ready when needed (production).
- **Negative:** NoSQL schema requires discipline — enforce with Pydantic models at the API layer.
- **Rejected Alternative:** Azure SQL — too rigid for evolving agent trace schemas.
- **Rejected Alternative:** Redis — volatile, not suitable for permanent audit trail.
