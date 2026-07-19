# Direct 32B Access Policy

## Finding

Direct vLLM 32B chat endpoint returns HTTP 200. Completion-only policy is enforced by gateway, not by vLLM itself.

## MVP policy

For MVP, user-facing clients must not call direct `vllm-32b-gptq` Service.
All user-facing 32B traffic must go through `nginx-gateway-32b`.

## Status

ACCEPTED FOR MVP / VERIFY IN BFF AND PORTAL STAGES

## Required follow-up

- Stage 05 BFF must route 32B only through gateway.
- Stage 07 Portal must call BFF only, not direct vLLM.
- Stage 08/11 should include synthetic probe for direct path policy or network policy decision.

## Risk

If internal clients can call direct vLLM service, 32B chat restriction can be bypassed.

## Current decision

Accepted for MVP internal cluster scope, but must be enforced by BFF/Portal routing and later NetworkPolicy if available.
