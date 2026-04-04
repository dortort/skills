# ISC2 CPE Submission — Shadow DOM Primitives & Reference

## Shadow DOM Traversal

Every discovery or interaction function must recursively walk Shadow DOM:
```javascript
function walkShadowDOM(root, callback, depth = 0) {
  if (depth > 15) return;
  callback(root, depth);
  const elements = root.querySelectorAll ? root.querySelectorAll('*') : [];
  for (const el of elements) {
    if (el.shadowRoot) walkShadowDOM(el.shadowRoot, callback, depth + 1);
  }
}
```

### Context Persistence

Helper functions defined inside `page.evaluate()` do NOT survive across page navigations. The Salesforce SPA uses client-side routing that resets the JS context on navigation. Two approaches:

1. **Re-inject in every evaluate call** — define `walkShadowDOM` and helpers inside each `page.evaluate()` callback. Simplest but verbose.
2. **Attach to `window`** — set `window.walkShadowDOM = ...` and re-inject after each navigation step.

With the per-step CDP architecture, each step script runs in a fresh Node.js process, so you must inject helpers in every script's `page.evaluate()` calls.

## Setting Text Input Values (Native Setter Pattern)

Salesforce LWC intercepts `el.value = ...` on text inputs and silently discards values that bypass its reactivity system. Use the native HTMLInputElement prototype setter, then dispatch events:
```javascript
function setInputValue(el, value) {
  const nativeSetter = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype, 'value'
  ).set;
  nativeSetter.call(el, value);
  ['focus', 'input', 'change', 'blur', 'focusout'].forEach(e =>
    el.dispatchEvent(new Event(e, { bubbles: true }))
  );
}
```

**Exception — decimal/number inputs** (like Credits): The native setter returns empty on these. Use direct assignment instead:
```javascript
function setDecimalInputValue(el, value) {
  el.value = value;
  ['focus', 'input', 'change', 'blur', 'focusout'].forEach(e =>
    el.dispatchEvent(new Event(e, { bubbles: true }))
  );
}
```

How to tell which to use: if `el.inputMode === 'decimal'` or `el.step`, use direct assignment. Otherwise use the native setter.

## Setting Lightning Combobox Values

The category selector is a `<lightning-combobox>`, NOT a `<select>`. It renders as a `<button role="combobox">` with a `[role="listbox"]` dropdown. Do NOT use `setSelectValue` for this component.

**Discovering options:**
```javascript
// First, click the combobox button to open the dropdown
await page.evaluate(() => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('button[role="combobox"]')) {
      el.click();
    }
  });
});
await page.waitForTimeout(1000);

// Then discover available options
const options = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('[role="option"]')) {
      const value = el.getAttribute('data-value') || '';
      const text = el.textContent?.trim() || '';
      if (value) results.push({ text, value });
    }
  });
  return results;
});
```

**Selecting an option:**
```javascript
await page.evaluate((targetValue) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('[role="option"]')) {
      if (el.getAttribute('data-value') === targetValue) {
        el.click();
        return;
      }
    }
  });
}, 'Education');
await page.waitForTimeout(2000); // Wait for radio buttons to update
```

## Setting Select Dropdown Values

Use this for standard `<select>` elements in detail fields (NOT for the category combobox):
```javascript
function setSelectValue(el, value) {
  const nativeSetter = Object.getOwnPropertyDescriptor(
    HTMLSelectElement.prototype, 'value'
  ).set;
  nativeSetter.call(el, value);
  el.dispatchEvent(new Event('change', { bubbles: true }));
}
```

## Clicking Shadow DOM Elements (Radio Buttons, Checkboxes)

Never use coordinate-based clicks — there is a persistent vertical offset between visual position and actual click targets on this site. Always use `el.click()` via `page.evaluate()` with Shadow DOM traversal.

## Dismissing Dialogs

Dismiss blocking dialogs before each interaction step:
```javascript
await page.evaluate(() => {
  // Salesforce CSS error dialog
  document.getElementById('dismissError')?.click();
  // OneTrust cookie banner
  document.querySelector('.onetrust-close-btn-handler')?.click();
  document.querySelector('button#onetrust-reject-all-handler')?.click();
});
```

## CDP Connection Boilerplate

Every per-step script starts with this:
```javascript
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const context = browser.contexts()[0];
  const page = context.pages()[0];

  // Dismiss dialogs
  await page.evaluate(() => {
    document.getElementById('dismissError')?.click();
    document.querySelector('button#onetrust-reject-all-handler')?.click();
  });

  // Inject helpers into page context
  await page.evaluate(() => {
    window.walkShadowDOM = function(root, cb, d) {
      d = d || 0; if (d > 15) return; cb(root, d);
      var els = root.querySelectorAll ? root.querySelectorAll('*') : [];
      for (var i = 0; i < els.length; i++) {
        if (els[i].shadowRoot) window.walkShadowDOM(els[i].shadowRoot, cb, d + 1);
      }
    };
    window.setInputValue = function(el, value) {
      var ns = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      ns.call(el, value);
      ['focus','input','change','blur','focusout'].forEach(function(e) {
        el.dispatchEvent(new Event(e, { bubbles: true }));
      });
    };
    window.setDecimalInputValue = function(el, value) {
      el.value = value;
      ['focus','input','change','blur','focusout'].forEach(function(e) {
        el.dispatchEvent(new Event(e, { bubbles: true }));
      });
    };
  });

  // ... perform ONE step ...
  // Print results as JSON for the agent to read
  console.log(JSON.stringify({ ok: true, result: '...' }));

  // Disconnect (does NOT close the browser)
  browser.close();
})();
```

## Detailed Code Examples

### Step 0: Snapshot Existing Drafts

Before starting any submission, record existing drafts so only new ones are cleaned up later:
```javascript
const drafts = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const tr of root.querySelectorAll('tr')) {
      const cells = Array.from(tr.querySelectorAll('td'));
      if (cells.length >= 6) {
        const lastModified = cells[0]?.textContent?.trim() || '';
        const name = cells[1]?.textContent?.trim() || '';
        const status = cells[5]?.textContent?.trim() || '';
        if (status === 'Draft') {
          results.push({ lastModified, name });
        }
      }
    }
  });
  return results;
});
console.log(JSON.stringify({ ok: true, existingDrafts: drafts }));
```

### Step 1: Setting Dates

```javascript
await page.evaluate(({ startDate, endDate }) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="text"]')) {
      if (el.name === 'start-date') setInputValue(el, startDate);
      if (el.name === 'end-date') setInputValue(el, endDate);
    }
  });
}, { startDate: 'Dec 11, 2025', endDate: 'Dec 11, 2025' });

// Verify Continue button is enabled
const continueEnabled = await page.evaluate(() => {
  const btn = document.getElementById('continueButton');
  return btn ? !btn.disabled : false;
});
console.log(JSON.stringify({ ok: continueEnabled }));

if (continueEnabled) {
  await page.click('#continueButton');
  await page.waitForURL('**/cpeportalcategorydetailpage', { timeout: 15000 });
}
```

### Step 2a: Discovering & Setting Category

```javascript
// Open combobox
await page.evaluate(() => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('button[role="combobox"]')) {
      el.click();
    }
  });
});
await page.waitForTimeout(1000);

// Discover options
const options = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('[role="option"]')) {
      const value = el.getAttribute('data-value') || '';
      const text = el.textContent?.trim() || '';
      if (value) results.push({ text, value });
    }
  });
  return results;
});
console.log(JSON.stringify({ ok: true, options }));

// Select option (e.g., "Education")
await page.evaluate((targetValue) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('[role="option"]')) {
      if (el.getAttribute('data-value') === targetValue) { el.click(); return; }
    }
  });
}, 'Education');
await page.waitForTimeout(2000);
```

### Step 2b: Discovering & Selecting CPE Type Radio

```javascript
const cpeTypes = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="radio"]')) {
      const label = el.nextElementSibling?.textContent?.trim() || '';
      if (label && el.name === 'radioGroupRequired') results.push(label);
    }
  });
  return results;
});
console.log(JSON.stringify({ ok: true, cpeTypes }));

await page.evaluate((targetLabel) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="radio"]')) {
      if ((el.nextElementSibling?.textContent?.trim() || '') === targetLabel) {
        el.click();
      }
    }
  });
}, 'Industry Conference');
await page.waitForTimeout(2500);
```

### Step 2c: Discovering & Filling Detail Fields

```javascript
// Discover fields
const detailFields = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input, select, textarea')) {
      if (el.tagName === 'INPUT' && ['text', 'number', 'date', 'url'].includes(el.type)) {
        const parentLabel = el.closest('lightning-input')?.getAttribute('label') || '';
        results.push({
          tag: 'INPUT', name: el.name, label: parentLabel, type: el.type,
          inputMode: el.inputMode, step: el.step, required: el.required, value: el.value
        });
      }
      if (el.tagName === 'SELECT') {
        results.push({
          tag: 'SELECT',
          options: Array.from(el.options).map(o => ({ text: o.text, value: o.value }))
        });
      }
      if (el.tagName === 'TEXTAREA') {
        const parentLabel = el.closest('lightning-textarea')?.getAttribute('label') || '';
        results.push({ tag: 'TEXTAREA', name: el.name, label: parentLabel, required: el.required });
      }
    }
  });
  return results;
});
console.log(JSON.stringify({ ok: true, fields: detailFields }));

// Fill fields (adapt field names based on discovery results)
await page.evaluate((values) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input')) {
      if (!['text', 'number', 'url'].includes(el.type)) continue;
      const name = el.name || '';
      if (name in values) {
        if (el.inputMode === 'decimal' || el.step) {
          setDecimalInputValue(el, values[name]);
        } else {
          setInputValue(el, values[name]);
        }
      }
    }
    for (const el of root.querySelectorAll('textarea')) {
      const name = el.name || '';
      if (name in values) {
        const ns = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
        ns.call(el, values[name]);
        ['focus', 'input', 'change', 'blur', 'focusout'].forEach(e =>
          el.dispatchEvent(new Event(e, { bubbles: true }))
        );
      }
    }
  });
}, {
  Label__c: 'DevOpsDays Tel Aviv 2025',
  HostingOrganizationSponsor__c: 'TLVCommunity / DevOpsDays',
  Credits__c: '8',
  ReviewText__c: 'Attended DevOpsDays Tel Aviv 2025...'
});

// Verify Save button is enabled
const saveEnabled = await page.evaluate(() => {
  const btn = document.getElementById('saveNextBtn');
  return btn ? !btn.disabled : false;
});
console.log(JSON.stringify({ ok: saveEnabled }));

if (saveEnabled) {
  await page.click('#saveNextBtn');
  await page.waitForURL('**/cpeportaldomainpage', { timeout: 15000 });
}
```

### Step 3: Discovering & Selecting Domains

```javascript
const domains = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="checkbox"]')) {
      const label = el.nextElementSibling?.textContent?.trim() || '';
      // Exclude OneTrust cookie checkboxes
      if (label && !el.name?.startsWith('ot-') && label !== 'checkbox label') {
        results.push({ label, checked: el.checked });
      }
    }
  });
  return results;
});
console.log(JSON.stringify({ ok: true, domains }));

// If all labels show "checkbox label", wait and retry
// This is a rendering timing issue

await page.evaluate((targetDomains) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="checkbox"]')) {
      const label = el.nextElementSibling?.textContent?.trim() || '';
      if (targetDomains.some(td => label.toLowerCase().includes(td.toLowerCase())) && !el.checked) {
        el.click();
      }
    }
  });
}, ['Security Operations', 'Software Development Security']);

await page.click('#saveNextBtn');
await page.waitForURL('**/cpeportalreviewpage', { timeout: 15000 });
```

### Step 4: Review & Submit

```javascript
const reviewText = await page.evaluate(() => document.body.innerText);
// Verify dates, title, credits, category, and domain are correct
console.log(JSON.stringify({ ok: true, review: reviewText.substring(0, 2000) }));

await page.click('button:has-text("Submit CPE")');
await page.waitForURL('**/cpeportalconfirmationpage', { timeout: 15000 });
```

### Step 5: Submit Another

```javascript
await page.click('button:has-text("Add Another CPE")');
await page.waitForURL('**/s/', { timeout: 10000 });
await page.waitForTimeout(1000);
```

### Draft Cleanup (Post-Submission)

Only delete drafts that were NOT present in the pre-submission snapshot:
```javascript
// Compare current drafts against the snapshot taken in Step 0
const currentDrafts = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const tr of root.querySelectorAll('tr')) {
      const cells = Array.from(tr.querySelectorAll('td'));
      if (cells.length >= 6 && cells[5]?.textContent?.trim() === 'Draft') {
        results.push({
          lastModified: cells[0]?.textContent?.trim() || '',
          name: cells[1]?.textContent?.trim() || ''
        });
      }
    }
  });
  return results;
});

// Identify new drafts (not in pre-submission snapshot)
// Delete each new draft by clicking its "delete this draft" button
// Drafts are deleted one at a time; no confirmation dialog is shown

await page.evaluate((preExistingCount) => {
  // Delete buttons appear in order; only click those beyond the pre-existing count
  let deleteButtons = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('button')) {
      if (el.textContent?.trim() === 'delete this draft') deleteButtons.push(el);
    }
  });
  // Delete from the end to avoid index shifting, skip pre-existing
  for (let i = deleteButtons.length - 1; i >= preExistingCount; i--) {
    deleteButtons[i].click();
  }
}, existingDraftCount);
```

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| CSS Error dialog ("Sorry to interrupt") | Salesforce aura framework error | `page.evaluate(() => document.getElementById('dismissError')?.click())` |
| Cookie consent dialog blocks interaction | OneTrust cookie banner | `page.evaluate(() => document.querySelector('button#onetrust-reject-all-handler')?.click())` |
| Text input values silently ignored | Did not use native HTMLInputElement setter | Use `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set` |
| Credits/decimal field empty after native setter | Native setter fails on `inputMode="decimal"` inputs | Use direct `el.value = ...` for fields with `el.inputMode === 'decimal'` or `el.step` |
| "Something went wrong!" after Save & Continue | Detail fields not registered by LWC reactivity | Dispatch full event sequence: focus → input → change → blur → focusout |
| Wrong checkbox/radio selected by coordinate click | Persistent vertical offset in Salesforce layout | Always use `el.click()` via `page.evaluate()` Shadow DOM traversal |
| Page renders blank or breaks layout | Salesforce layout fragile at unusual window sizes | Keep window at standard size (~1280x1024); avoid very large dimensions |
| Session expired / redirected to login | Cookie timeout | Re-run manual login against the persistent profile directory |
| Radio selection doesn't reveal detail fields | Click didn't register on Shadow DOM element | Ensure `el.click()` is called on the `<input type="radio">` itself, not a wrapper; add 2s wait after |
| Continue / Save button disabled | Required fields not filled or values not registered by LWC | Re-discover fields, check for unfilled required inputs, verify values were set via `page.evaluate()` |
| Category dropdown shows no `<select>` elements | Category is a `lightning-combobox`, not a `<select>` | Use `button[role="combobox"]` click → `[role="option"]` click pattern |
| Domain checkbox labels show "checkbox label" | Rendering timing issue | Wait 2–3s and re-discover; labels populate after LWC rendering completes |
| Helper functions undefined after navigation | `page.evaluate()` context resets on navigation | Re-inject helpers after each navigation or attach to `window` and re-inject per step |
