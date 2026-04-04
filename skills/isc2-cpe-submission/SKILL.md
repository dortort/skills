---
name: isc2-cpe-submission
description: Submit ISC2 CPE credits on cpe.isc2.org. Use when the user wants to log continuing education activities for CISSP, CCSP, or other ISC2 certifications.
argument-hint: [cpe-description]
disable-model-invocation: true
allowed-tools: Bash(npx:*) Read
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

## Authentication

Requires an active authenticated session via a persistent Playwright profile. Never handle credentials directly.

**First-time setup (manual, one-time):**
```bash
npx playwright open --browser chromium --user-data-dir=~/.isc2-profile https://cpe.isc2.org/s/
```
Log in through the ISC2 portal, then close the browser. If the session expires later, repeat this step.

**Launching the browser in scripts:**
```javascript
const { chromium } = require('playwright');
const browser = await chromium.launchPersistentContext(
  path.join(os.homedir(), '.isc2-profile'),
  { headless: false }
);
const page = browser.pages()[0] || await browser.newPage();
await page.goto('https://cpe.isc2.org/s/');
```

## Workflow Steps

Dismiss blocking dialogs (Salesforce error dialogs, OneTrust cookie banners) before each interaction step. See `reference.md` for the dismissal code.

### Step 1: Dates Page (`/s/`)

Discover two text inputs — Start Date and End Date. For single-day activities (blog post, webinar), both dates are the same. For multi-day activities (conferences, courses), they differ. Date format is `Mon DD, YYYY` (e.g., `Mar 09, 2026`). Set values using the native setter pattern, then click "Continue".

### Step 2a: Category Selection (`/s/cpeportalcategorydetailpage`)

Discover category dropdown options. Evaluate based on the user's CPE:
- Writing/publishing → "Contributions to the Profession"
- Attending a conference → "Education" or "Professional Development"
- Taking a course → "Education"
- Volunteer/board work → "Contributions to the Profession"

Set the dropdown using the native select setter. Wait 1s for radio buttons to update.

### Step 2b: CPE Type Radio Button

Discover available radio button labels (they change per category). Match the user's activity to the best label. Click the radio via `el.click()` in Shadow DOM — never by coordinates. Wait 2s for detail fields to render.

### Step 2c: Detail Fields

Discover the fields that appeared after radio selection (inputs, selects, textareas). Common fields:
- `Label__c` → Title/name of the CPE activity
- `Publisher__c` → Publisher or provider name
- `Yearpublished__c` → Year
- `Credits__c` → Number of CPE credits (decimal, 0.25–40)

Fill each field based on the user's description. For selects, read available options and pick the best semantic match. Use native setter for text inputs, direct assignment for decimal inputs. Click "Save & Continue".

### Step 3: Domain Selection (`/s/cpeportaldomainpage`)

Discover domain checkboxes (vary by certification). Choose the domain(s) most relevant to the CPE activity. At least one must be selected. Click checkboxes via `el.click()` in Shadow DOM. Click "Save & Continue".

### Step 4: Review & Submit (`/s/cpeportalreviewpage`)

Read the review page text to verify dates, title, credits, category, and domain are correct. Click "Submit CPE".

### Step 5: Confirmation (`/s/cpeportalconfirmationpage`)

Confirm "CPE Successfully Submitted!" message. To submit another CPE, click "Add Another CPE".

## Key Principles

1. **Discover before acting.** Never assume what options, fields, or checkboxes exist.
2. **Evaluate based on user intent.** Map the user's activity description to the best available option at each step.
3. **Shadow DOM traversal is mandatory** for all form elements. Only top-level navigation buttons (`Continue`, `Save & Continue`, `Back`, `Submit CPE`, `Add Another CPE`) work with standard Playwright selectors.
4. **Use native property setters** for text inputs. Use direct assignment for decimal/number inputs. Always dispatch the full event sequence.
5. **Never click by coordinates** on checkboxes or radio buttons.
6. **Use a headed browser with persistent profile** for authentication.

## URL Reference

| Step | URL Pattern |
|------|-------------|
| Dates (start) | `https://cpe.isc2.org/s/` |
| Category & Detail | `https://cpe.isc2.org/s/cpeportalcategorydetailpage` |
| Domain | `https://cpe.isc2.org/s/cpeportaldomainpage` |
| Review | `https://cpe.isc2.org/s/cpeportalreviewpage` |
| Confirmation | `https://cpe.isc2.org/s/cpeportalconfirmationpage` |
