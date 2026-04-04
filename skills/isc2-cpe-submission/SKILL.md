---
name: isc2-cpe-submission
description: Submit ISC2 CPE credits on cpe.isc2.org. Use when the user wants to log continuing education activities for CISSP, CCSP, or other ISC2 certifications.
argument-hint: [cpe-description]
disable-model-invocation: true
allowed-tools: Bash(node:*) Bash(npx:*) Read Write
---

# ISC2 CPE Submission

Submit CPE (Continuing Professional Education) credits on the ISC2 CPE portal (https://cpe.isc2.org/s/). The site is built on Salesforce LWC with heavy Shadow DOM usage. For all Shadow DOM primitives, input workarounds, and error troubleshooting, read `${CLAUDE_SKILL_DIR}/reference.md`.

This skill is generic to all CPE types — conferences, courses, blog posts, presentations, self-study, volunteer work, etc. Forms, categories, radio options, detail fields, and domain checkboxes vary by CPE type and may change over time.

## Core Pattern: Discover → Evaluate → Act

At every step:
1. **Discover** — Enumerate what the page currently offers (options, fields, checkboxes) using Shadow DOM traversal
2. **Evaluate** — Based on the user's CPE description, determine the best match
3. **Act** — Use Shadow DOM primitives from `reference.md` to make the selection

Never assume what options exist. Always read them from the live DOM first.

## Architecture: Per-Step Scripts with Persistent Browser

**CRITICAL: Never write a single monolithic script for the entire workflow.** Each workflow step must be a separate script execution. This prevents orphaned draft CPEs when a step fails.

1. Launch the browser once in background with CDP enabled (`--remote-debugging-port=9222`)
2. For each workflow step: write a small script that reconnects via CDP, performs discovery, prints results as JSON
3. Read the JSON output, decide next action based on actual DOM state, write the next step script
4. **Never write a script that spans more than one workflow step**

Why: failed steps don't create orphaned drafts, the agent adapts to actual DOM state, and there's no monolithic script rewrite cycle.

See `${CLAUDE_SKILL_DIR}/reference.md` for the launch script, CDP boilerplate, and helper injection pattern.

## Pre-Submission: Snapshot Existing Drafts

Before starting any submission, read the draft CPE table on the main `/s/` page and record the existing drafts (count, last-modified dates, names). This snapshot is used later for safe cleanup — only drafts created during this submission attempt should be deleted.

## Authentication

Requires an active authenticated session via a persistent Playwright profile. Never handle credentials directly.

**First-time setup (manual, one-time):**
```bash
npx playwright open --browser chromium --user-data-dir=~/.isc2-profile https://cpe.isc2.org/s/
```
Log in through the ISC2 portal, then close the browser. If the session expires later, repeat this step.

## Workflow Steps

Dismiss blocking dialogs (Salesforce error dialogs, OneTrust cookie banners) before each interaction step. See `reference.md` for the dismissal code.

### Step 1: Dates Page (`/s/`)

Discover two text inputs with `name="start-date"` and `name="end-date"`. For single-day activities, both dates are the same. For multi-day activities, they differ. Date format is `Mon DD, YYYY` (e.g., `Dec 11, 2025`).

Set values using the native setter pattern, then verify `#continueButton` is enabled (not disabled) before clicking it. If the button is still disabled after setting dates, the values were not registered — retry with a different approach (see `reference.md`).

### Step 2a: Category Selection (`/s/cpeportalcategorydetailpage`)

The category selector is a **`<lightning-combobox>`** component, NOT a standard `<select>`. It renders as a `<button role="combobox">`. To interact:
1. Click the combobox button to open the dropdown
2. Discover the available `[role="option"]` elements and their `data-value` attributes
3. Click the matching option

Always discover options from the live DOM. As a fallback hint if discovery returns unexpected results, known category `data-value` attributes have included:
- `ContributionstotheProfession` — Writing/publishing, board work, volunteer
- `Education` — Conferences, courses, seminars, webinars
- `ProfessionalDevelopment` — Professional development activities
- `UniqueWorkExperience` — Unique work experience

Evaluate based on the user's CPE type. Wait 1–2s for radio buttons to update after selection.

### Step 2b: CPE Type Radio Button

Discover available radio button labels (they change per category). Radio buttons have `name="radioGroupRequired"` and labels are in `el.nextElementSibling.textContent`. Match the user's activity to the best label. Click the radio via `el.click()` in Shadow DOM — never by coordinates. Wait 2s for detail fields to render.

As a fallback hint, radio options previously seen under "Education" include:
- Book, Magazine, Whitepaper
- Courses and Seminars - Other
- Higher Education Course
- **Industry Conference** ← use for conferences/events
- Information security professional association chapter meeting
- ISC2 Certification Course
- ISC2 Continuing Education Course
- Online webinars, podcasts and other online materials
- Vendor Presentation

### Step 2c: Detail Fields

Discover the fields that appeared after radio selection. **Field names vary per CPE type** — always discover, never hardcode.

As a fallback hint, field mappings previously seen by CPE type:

| CPE Type | Fields |
|----------|--------|
| Industry Conference | `Label__c` (title), `HostingOrganizationSponsor__c` (organizer), `Credits__c` (decimal), `ReviewText__c` (description) |
| Courses and Seminars | `Label__c` (title), `TrainingProviderOrganization__c` (provider), `Credits__c` (decimal), `ReviewText__c` (description) |
| Writing/Publishing | `Label__c` (title), `Publisher__c` (publisher), `Yearpublished__c` (year), `Credits__c` (decimal) |

Fill each field based on the user's description. Use native setter for text inputs, direct assignment for decimal inputs (`el.inputMode === 'decimal'` or `el.step`). Always dispatch the full event sequence.

After filling, verify `#saveNextBtn` is **enabled** (not disabled). If disabled, a required field is missing — re-discover fields and check which ones are empty. Click "Save & Continue" only when the button is enabled.

### Step 3: Domain Selection (`/s/cpeportaldomainpage`)

Discover domain checkboxes (vary by certification). Domain checkboxes may have rendering timing issues — if labels show as "checkbox label", wait 2–3s and re-discover. Choose the domain(s) most relevant to the CPE activity. At least one must be selected. Click checkboxes via `el.click()` in Shadow DOM. Exclude checkboxes with `name` starting with `ot-` (those are cookie consent checkboxes). Click "Save & Continue".

### Step 4: Review & Submit (`/s/cpeportalreviewpage`)

Read the review page text to verify dates, title, credits, category, and domain are correct. Click "Submit CPE".

### Step 5: Confirmation (`/s/cpeportalconfirmationpage`)

Confirm "CPE Successfully Submitted!" message. To submit another CPE, click "Add Another CPE".

## Batch Submissions

When the user provides multiple CPE activities (e.g., "submit CPEs for these 12 blog articles"), treat each as a full loop through Steps 1–5 → "Add Another CPE".

**Input:** The user may provide a list inline, reference a file, or describe a pattern ("all blog posts from 2025"). Parse the list into individual items before starting. Confirm the parsed list with the user before submitting.

**Workflow:**
1. Snapshot existing drafts once before the entire batch (Step 0)
2. For each item: run Steps 1–5, then click "Add Another CPE" to return to the dates page
3. Track per-item status: record which items succeeded and which failed (with the failure reason)
4. On individual item failure: log the error, navigate back to `/s/`, and continue to the next item
5. After the entire batch: perform draft cleanup once, report results to the user

**Shared fields:** For batch items of the same type (e.g., all blog articles), the category, CPE type, and some detail fields will be identical. Still re-select them each iteration — the portal resets the form after each submission. However, you can reuse the discovered options from the first iteration to speed up evaluation in subsequent ones, as long as you verify the options are still present.

**Reporting:** After the batch completes, summarize:
- Total submitted / total attempted
- Per-item status (title + success/failure)
- Any drafts cleaned up
- Items that need manual retry

## Post-Submission: Draft Cleanup

After submission (successful or failed), navigate back to `/s/` and check for draft CPEs. Compare against the pre-submission snapshot. **Only delete drafts that were NOT present before the submission began** — match by last-modified date and name/status. Pre-existing drafts must be left untouched.

To delete a draft: click its "delete this draft" button. No confirmation dialog is required — the draft is deleted immediately.

## Button Reference

| Button | ID | Disabled When | Selector |
|--------|----|---------------|----------|
| Continue | `#continueButton` | Dates not set or invalid | `page.click('#continueButton')` |
| Save & Continue | `#saveNextBtn` | Required detail fields missing | `page.click('#saveNextBtn')` |
| Submit CPE | — | — | `page.click('button:has-text("Submit CPE")')` |
| Add Another CPE | — | — | `page.click('button:has-text("Add Another CPE")')` |

Prefer ID selectors over `has-text` selectors for reliability. Always check the `disabled` property before clicking — if disabled, a prerequisite is not met.

## Key Principles

1. **One step per script.** Never combine multiple workflow steps in a single script execution.
2. **Discover before acting.** Never assume what options, fields, or checkboxes exist.
3. **Evaluate based on user intent.** Map the user's activity description to the best available option at each step.
4. **Shadow DOM traversal is mandatory** for all form elements.
5. **Use native property setters** for text inputs. Use direct assignment for decimal/number inputs. Always dispatch the full event sequence.
6. **Never click by coordinates** on checkboxes or radio buttons.
7. **Check button disabled state** before clicking navigation buttons. If disabled, a prerequisite is missing.
8. **Preserve pre-existing drafts.** Only clean up drafts created during the current submission attempt.

## URL Reference

| Step | URL Pattern |
|------|-------------|
| Dates (start) | `https://cpe.isc2.org/s/` |
| Category & Detail | `https://cpe.isc2.org/s/cpeportalcategorydetailpage` |
| Domain | `https://cpe.isc2.org/s/cpeportaldomainpage` |
| Review | `https://cpe.isc2.org/s/cpeportalreviewpage` |
| Confirmation | `https://cpe.isc2.org/s/cpeportalconfirmationpage` |
