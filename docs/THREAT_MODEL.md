# Threat model

## Protected assets

- Tenant documents and role-restricted excerpts.
- Database connection strings and model API keys.
- Non-allowlisted tables, rows beyond the response cap and database write capability.
- Integrity of evaluation cases and published claims.

## Trust boundaries and controls

| Threat | Control | Residual risk |
|---|---|---|
| Forged tenant or role | JWT signature, issuer, audience and expiry verification | Key compromise requires rotation and external identity controls |
| Cross-tenant RAG leakage | Tenant/role predicates before ranking; cross-tenant tests | Misconfigured ingestion metadata remains an operational risk |
| Unsupported answer | Evidence threshold, refusal and citations | Live model can still paraphrase poorly; evaluate separately |
| Prompt asks for destructive SQL | One-query AST allowlist and dangerous-function blocks | Parser/library bugs; database read-only role provides containment |
| Model names hidden table | Authorized schema input plus table allowlist validation | Allowlisted tables may still contain overbroad columns |
| SQL consumes excessive resources | Statement timeout, LIMIT clamp and row cap | Expensive plans below timeout remain possible |
| Repair bypasses policy | One repair maximum; repaired candidate uses same validator | Model/provider availability still affects completion |
| Credential disclosure | Fernet at rest; `SecretStr`; no-echo API models; ignored runtime env | Host or process compromise is outside this demo boundary |
| External model receives private data | Online mode is explicit; only accessible excerpts/schema sent | Provider retention and residency require production governance |
| Inflated evaluation claim | Fixed hashes, checked counts, JSON failures and explicit limitations | Synthetic coverage cannot guarantee unseen behavior |

## Production follow-ups

- Integrate an enterprise identity provider and short-lived signing-key rotation.
- Use a managed secret store/KMS and network-isolated per-tenant database roles.
- Add column/row policies, query cost inspection and rate limits for structured data.
- Add prompt/output redaction plus auditable tracing with retention controls.
- Run external red-team and live-model evaluations as separate versioned reports.
