# Terraform → Wrangler Resource Mapping

This reference maps Cloudflare Terraform resource types to their corresponding Wrangler configuration fields. Use it to know which Terraform outputs to create and which template tokens to define.

## Resource Mapping Table

| Resource | Terraform Resource | Terraform Output | Wrangler Config Field | Template Token |
|---|---|---|---|---|
| KV Namespace | `cloudflare_workers_kv_namespace` | `.id` | `kv_namespaces[].id` | `__KV_NAMESPACE_ID__` |
| D1 Database | `cloudflare_d1_database` | `.id` | `d1_databases[].database_id` | `__D1_DATABASE_ID__` |
| R2 Bucket | `cloudflare_r2_bucket` | `.name` | `r2_buckets[].bucket_name` | `__R2_BUCKET_NAME__` |
| Queue (producer) | `cloudflare_queue` | `.name` | `queues.producers[].queue` | `__QUEUE_NAME__` |
| Queue (consumer) | `cloudflare_queue` | `.name` | `queues.consumers[].queue` | `__QUEUE_NAME__` |
| Service Binding | `cloudflare_workers_script` | `.name` | `services[].service` | `__SERVICE_NAME__` |
| Analytics Engine | `cloudflare_workers_analytics_engine_dataset` | `.dataset` | `analytics_engine_datasets[].dataset` | `__ANALYTICS_DATASET__` |
| Zone ID | `cloudflare_zone` | `.id` | `routes[].zone_id` or top-level | `__ZONE_ID__` |
| Account ID | variable / data source | `var.account_id` | `account_id` | `__ACCOUNT_ID__` |

## Notes

- **Naming convention**: Template tokens use `__UPPER_SNAKE_CASE__` matching the Terraform output name. If your output is `staging_kv_namespace_id`, the token is `__STAGING_KV_NAMESPACE_ID__`.
- **Multiple bindings**: If a Worker binds to multiple KV namespaces, create separate Terraform outputs for each (e.g., `cache_kv_id`, `session_kv_id`) and separate tokens.
- **Terraform v5 provider**: Resource type names changed from v4 to v5. The table above uses v5 names. If using v4, check the migration guide.

## Wrangler Config Formats

Wrangler supports both TOML (`wrangler.toml`) and JSON (`wrangler.jsonc`). The bridge script pattern works with either, but JSON is recommended for new projects because:

1. Cloudflare recommends it going forward
2. Some newer Wrangler features are JSON-only
3. JSON is easier to programmatically generate and validate

If the project uses TOML, the sync script needs a TOML writer (e.g., `@iarna/toml`) or you can use `sed`-style replacement on the template. JSON avoids this dependency.
