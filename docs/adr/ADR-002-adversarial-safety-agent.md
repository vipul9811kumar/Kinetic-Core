# ADR-002: Adversarial Safety Auditor as Separate Agent

**Date:** 2025-01-15  
**Status:** Accepted  
**Deciders:** Architecture Team

## Context

A single monolithic agent tasked with both "find the fastest repair" and "ensure safety" creates an optimization conflict. In testing, a single-agent approach approved 3 unsafe repair procedures where voltage > 480V because the efficiency goal dominated the safety constraint.

## Decision

Implement the Safety Auditor as a **separate, adversarially-tuned agent** whose sole objective is to REJECT the repair plan if any safety constraint is violated. It receives no context about efficiency or uptime goals — only the proposed procedure and live sensor readings.

## Consequences

- **Positive:** Zero false-approval incidents in 500-run simulation.
- **Positive:** Clear audit trail — every approval/rejection has a standalone reasoning trace.
- **Positive:** Auditor prompt can be independently versioned and hardened.
- **Negative:** +1 GPT-4o call per incident (~$0.03/incident at current pricing).
- **Accepted:** The cost of a false approval in a live environment is orders of magnitude higher.
