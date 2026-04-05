---
name: cloudflare-iac
description: "Best practices for Cloudflare infrastructure as code using Terraform and Wrangler together. Use this skill whenever the user is setting up Cloudflare Workers, Pages, KV, D1, R2, Queues, or other Wrangler-managed resources alongside Terraform — especially when they need to pass resource IDs between Terraform and Wrangler, automate deployments via CI/CD, or structure a Cloudflare project for infrastructure as code. Also trigger when the user mentions 'Terraform and Wrangler,' 'Cloudflare IaC,' 'wrangler.toml from Terraform,' 'Cloudflare CI/CD,' or asks how to connect Terraform-managed resources to Workers."
---

# Cloudflare IaC: Terraform + Wrangler

## The Core Problem

Cloudflare's tooling is split between two worlds:

- **Terraform** manages infrastructure: zones, DNS records, access policies, firewall rules, account-level settings, and the *existence* of resources like KV namespaces, D1 databases, R2 buckets, and Queues.
- **Wrangler** manages application deployment: Worker code, Pages projects, bindings to those resources, and local development.

The challenge is that Wrangler needs resource IDs that Terraform creates. A KV namespace ID, a D1 database ID, a Queue name — these are outputs of `terraform apply` that must flow into `wrangler.toml` (or `wrangler.jsonc`) before `wrangler deploy` can work.

This skill codifies a DRY, automatable pattern for bridging that gap.

## Separation of Responsibilities

### Terraform Owns

- Zones and DNS records
- KV namespaces (`cloudflare_workers_kv_namespace`)
- D1 databases (`cloudflare_d1_database`)
- R2 buckets (`cloudflare_r2_bucket`)
- Queues (`cloudflare_queue`)
- Access policies, WAF rules, page rules
- Account-level settings
- Any resource that should exist before application code deploys

### Wrangler Owns

- Worker source code and bundling
- Pages project deployment
- Bindings configuration (connecting Workers to the resources Terraform created)
- Local development (`wrangler dev`)
- Secrets (via `wrangler secret put`)
- Deployment (`wrangler deploy`)

### The Gray Zone

Some resources can be managed by either tool. The guiding principle: **if multiple Workers or projects share a resource, Terraform owns it. If it's scoped to a single Worker, Wrangler can own it.** When in doubt, prefer Terraform — it gives you state tracking, drift detection, and a single source of truth for infrastructure.

Wrangler's auto-provisioning feature (which creates KV/R2/D1 resources on first deploy) is convenient for prototyping but should not be used in production pipelines. It creates resources outside of Terraform's state, leading to drift and resources that can't be managed or torn down systematically.

## The Bridge Pattern

### Overview

```
terraform apply → terraform output -json → bridge script → wrangler.jsonc → wrangler deploy
```

The bridge script is a Node.js script in the project, invoked via `package.json`. It reads Terraform outputs and writes them into Wrangler's config file. The same script runs locally and in CI/CD — no duplication.

### Step 1: Terraform Outputs

Define outputs for every resource ID that Wrangler needs:

```hcl
# outputs.tf

output "kv_namespace_id" {
  value = cloudflare_workers_kv_namespace.my_kv.id
}

output "d1_database_id" {
  value = cloudflare_d1_database.my_db.id
}

output "r2_bucket_name" {
  value = cloudflare_r2_bucket.my_bucket.name
}

output "account_id" {
  value = var.cloudflare_account_id
}

output "zone_id" {
  value = cloudflare_zone.my_zone.id
}
```

### Step 2: The Bridge Script

Create `scripts/sync-wrangler-config.mjs` — a Node.js script that reads Terraform outputs and generates (or patches) the Wrangler config:

```js
#!/usr/bin/env node

// scripts/sync-wrangler-config.mjs
//
// Reads Terraform outputs and writes wrangler.jsonc with the correct resource IDs.
// Run locally or in CI — same command, same result.

import { execSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

// --- Configuration ---
// Adjust these paths to match your project layout.
const TERRAFORM_DIR = join(ROOT, "terraform");
const WRANGLER_CONFIG_PATH = join(ROOT, "wrangler.jsonc");
const TEMPLATE_PATH = join(ROOT, "wrangler.template.jsonc");

// --- Read Terraform outputs ---
function getTerraformOutputs() {
  try {
    const raw = execSync("terraform output -json", {
      cwd: TERRAFORM_DIR,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    });
    const outputs = JSON.parse(raw);
    // terraform output -json wraps each value in { value, type, sensitive }
    const flat = {};
    for (const [key, entry] of Object.entries(outputs)) {
      flat[key] = entry.value;
    }
    return flat;
  } catch (err) {
    console.error("Failed to read Terraform outputs. Have you run 'terraform apply'?");
    console.error(err.message);
    process.exit(1);
  }
}

// --- Generate Wrangler config ---
function generateConfig(outputs) {
  if (!existsSync(TEMPLATE_PATH)) {
    console.error(`Template not found: ${TEMPLATE_PATH}`);
    console.error("Create a wrangler.template.jsonc with __PLACEHOLDER__ tokens.");
    process.exit(1);
  }

  let template = readFileSync(TEMPLATE_PATH, "utf-8");

  // Replace __PLACEHOLDER__ tokens with Terraform output values.
  // Token format: __UPPER_SNAKE_CASE__ mapping to terraform output names.
  for (const [key, value] of Object.entries(outputs)) {
    const token = `__${key.toUpperCase()}__`;
    template = template.replaceAll(token, String(value));
  }

  // Warn about unreplaced tokens
  const remaining = template.match(/__[A-Z_]+__/g);
  if (remaining) {
    console.warn("Warning: unreplaced tokens in template:", [...new Set(remaining)]);
  }

  writeFileSync(WRANGLER_CONFIG_PATH, template, "utf-8");
  console.log(`Wrote ${WRANGLER_CONFIG_PATH}`);
}

// --- Main ---
const outputs = getTerraformOutputs();
generateConfig(outputs);
```

### Step 3: The Template

Create `wrangler.template.jsonc` — a Wrangler config with placeholder tokens where Terraform outputs go:

```jsonc
{
  // Generated from wrangler.template.jsonc by scripts/sync-wrangler-config.mjs
  // Do not edit directly — edit the template instead.
  "name": "my-worker",
  "main": "src/index.ts",
  "compatibility_date": "2025-01-01",
  "account_id": "__ACCOUNT_ID__",

  "kv_namespaces": [
    {
      "binding": "MY_KV",
      "id": "__KV_NAMESPACE_ID__"
    }
  ],

  "d1_databases": [
    {
      "binding": "MY_DB",
      "database_id": "__D1_DATABASE_ID__",
      "database_name": "my-db"
    }
  ],

  "r2_buckets": [
    {
      "binding": "MY_BUCKET",
      "bucket_name": "__R2_BUCKET_NAME__"
    }
  ]
}
```

### Step 4: package.json Scripts

```json
{
  "scripts": {
    "sync": "node scripts/sync-wrangler-config.mjs",
    "predeploy": "npm run sync",
    "deploy": "wrangler deploy",
    "dev": "npm run sync && wrangler dev"
  }
}
```

`npm run deploy` automatically runs `sync` first (via the `predeploy` hook). The same `npm run deploy` command works locally and in CI/CD — DRY.

### Step 5: .gitignore

```gitignore
# Generated by sync script — do not commit
wrangler.jsonc

# Terraform
terraform/.terraform/
terraform/*.tfstate*
```

The generated `wrangler.jsonc` should not be committed. The template and the sync script are the source of truth.

## CI/CD Integration

The CI/CD pipeline runs the exact same commands a developer runs locally. The only difference is how Terraform state and credentials are provided.

### Generic Pipeline Structure

```yaml
# Pseudocode — adapt to your CI/CD platform's syntax

steps:
  # 1. Terraform applies infrastructure changes
  - name: terraform
    run: |
      cd terraform
      terraform init
      terraform apply -auto-approve

  # 2. Bridge script syncs Terraform outputs into Wrangler config
  # 3. Wrangler deploys the application
  - name: deploy-worker
    run: npm run deploy
    env:
      CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

That's it. `npm run deploy` calls `predeploy` → `sync` → `wrangler deploy`. Same as local.

### Credentials

- **Terraform**: needs a Cloudflare API token with permission to manage infrastructure resources. Provide via `CLOUDFLARE_API_TOKEN` env var or in the provider config.
- **Wrangler**: needs a Cloudflare API token with permission to deploy Workers. Often the same token, but can be scoped separately for least privilege.
- **Terraform state**: use a remote backend (S3, GCS, Terraform Cloud, etc.) so CI and local share the same state.

### Environment Promotion

For multi-environment setups (staging, production), use Terraform workspaces or separate state files, and Wrangler environments:

```jsonc
// In wrangler.template.jsonc
{
  "name": "my-worker",
  "env": {
    "staging": {
      "kv_namespaces": [{ "binding": "MY_KV", "id": "__STAGING_KV_NAMESPACE_ID__" }]
    },
    "production": {
      "kv_namespaces": [{ "binding": "MY_KV", "id": "__PRODUCTION_KV_NAMESPACE_ID__" }]
    }
  }
}
```

The sync script handles this naturally — just add the corresponding Terraform outputs.

## Alternative: Terraform-Managed Bindings

For teams that want Terraform as the single source of truth for everything — including deployment — the `cloudflare_worker_version` resource can manage bindings directly. In this model, Wrangler only bundles the code and Terraform handles the upload and binding wiring:

```hcl
resource "cloudflare_worker_version" "my_worker" {
  account_id         = var.cloudflare_account_id
  worker_id          = cloudflare_worker.my_worker.id
  main_module        = "index.js"
  compatibility_date = "2025-01-01"

  bindings = [
    {
      type         = "kv_namespace"
      name         = "MY_KV"
      namespace_id = cloudflare_workers_kv_namespace.my_kv.id
    },
    {
      type = "d1"
      name = "DB"
      id   = cloudflare_d1_database.my_db.id
    },
    {
      type        = "r2_bucket"
      name        = "MY_BUCKET"
      bucket_name = cloudflare_r2_bucket.my_bucket.name
    }
  ]
}
```

With this approach:
- `wrangler deploy --dry-run --outdir dist` bundles the code
- Terraform uploads the bundle and wires all bindings via resource references
- No bridge script, no template — Terraform resolves IDs natively

**Trade-off**: You lose Wrangler's local dev ergonomics for binding configuration. You'll still need a `wrangler.toml` for `wrangler dev`, which means some duplication. The bridge pattern (above) is generally better when developers actively use `wrangler dev`, while the Terraform-only approach suits CI-first workflows where local dev uses mocks or a minimal config.

Choose the bridge pattern when the team runs `wrangler dev` regularly. Choose Terraform-managed bindings when Terraform is already the deployment tool and local dev doesn't need real bindings.

## Type Safety: `wrangler types --check`

After generating or updating the Wrangler config, run `wrangler types` to regenerate TypeScript bindings. In CI, use `--check` to fail the build if types are stale:

```json
{
  "scripts": {
    "typecheck": "wrangler types --check",
    "predeploy": "npm run sync && npm run typecheck",
    "deploy": "wrangler deploy"
  }
}
```

This catches mismatches between Terraform-managed resources and the Worker's TypeScript types before deployment.

## Adapting to an Existing Project

When applying this pattern to a project that already exists:

1. **Audit what exists.** Look at the current `wrangler.toml`/`wrangler.jsonc` for hardcoded resource IDs. Check if Terraform is already in use. Look at CI/CD config.

2. **Identify the resources.** List every resource ID in the Wrangler config. Determine which are already in Terraform and which need to be imported.

3. **Import existing resources into Terraform** using `terraform import` rather than recreating them. This avoids downtime and data loss.

4. **Create the template.** Copy the existing Wrangler config to `wrangler.template.jsonc` and replace hardcoded IDs with `__PLACEHOLDER__` tokens.

5. **Write the bridge script.** Start with the reference script above and adjust paths and output names.

6. **Wire up package.json.** Add `sync`, `predeploy`, and `deploy` scripts.

7. **Update CI/CD.** Replace any manual ID-passing or config-generation steps with `npm run deploy`.

8. **Add `wrangler.jsonc` to `.gitignore`** once the generated file is confirmed working.

## Common Patterns

### Multiple Workers in a Monorepo

When a repo contains multiple Workers, each gets its own template and the sync script handles all of them:

```
project/
├── terraform/
├── workers/
│   ├── api/
│   │   ├── src/
│   │   └── wrangler.template.jsonc
│   └── cron/
│       ├── src/
│       └── wrangler.template.jsonc
├── scripts/
│   └── sync-wrangler-config.mjs
└── package.json
```

The sync script iterates over worker directories and applies the same token-replacement logic to each template.

### Secrets

Secrets should not go through the bridge script or template. Use `wrangler secret put` (interactive) or `wrangler secret bulk` (from a JSON file, useful in CI). Secrets are managed per-Worker in Cloudflare's API, not in config files.

In CI:
```bash
echo '{"API_KEY":"...","DB_PASSWORD":"..."}' | wrangler secret bulk
```

### Preview Environments

For PR-based preview deployments, the sync script can accept an environment argument:

```json
{
  "scripts": {
    "deploy:preview": "npm run sync -- --env preview && wrangler deploy --env preview"
  }
}
```

## Troubleshooting

| Symptom | Likely Cause |
|---|---|
| `sync` fails with "Failed to read Terraform outputs" | Terraform hasn't been applied, or you're in the wrong directory. Run `terraform apply` first. |
| Unreplaced `__TOKENS__` in generated config | Terraform output name doesn't match the token. Check `terraform output` names match the uppercase token pattern. |
| Wrangler deploy fails with "resource not found" | The resource ID from Terraform is stale or from the wrong environment. Re-run `terraform apply` then `npm run sync`. |
| Drift between Terraform state and Cloudflare | A resource was modified outside Terraform (possibly by Wrangler auto-provisioning). Run `terraform plan` to detect and reconcile. |

## Reference

- `scripts/sync-wrangler-config.mjs` — The bridge script (see `scripts/` directory for a production-ready version with argument parsing and multi-worker support)
- `references/terraform-wrangler-mapping.md` — Maps Terraform resource types to their corresponding Wrangler config fields
