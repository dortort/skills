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

## Setting Select Dropdown Values

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

## Detailed Code Examples

### Step 1: Setting Dates

```javascript
await page.evaluate(({ startDate, endDate }) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="text"]')) {
      if (el.placeholder === 'Start Date' || el.ariaLabel === 'Start Date') setInputValue(el, startDate);
      if (el.placeholder === 'End Date' || el.ariaLabel === 'End Date') setInputValue(el, endDate);
    }
  });
}, { startDate: 'Mar 09, 2026', endDate: 'Mar 09, 2026' });
await page.click('button:has-text("Continue")');
await page.waitForURL('**/cpeportalcategorydetailpage', { timeout: 10000 });
```

### Step 2a: Discovering & Setting Category

```javascript
const categories = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('select')) {
      const opts = Array.from(el.options).map(o => ({ text: o.text, value: o.value }));
      if (opts.length > 1) results.push(...opts);
    }
  });
  return results;
});

await page.evaluate((categoryValue) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('select')) {
      if (Array.from(el.options).some(o => o.value === categoryValue)) {
        setSelectValue(el, categoryValue);
      }
    }
  });
}, chosenCategory);
await page.waitForTimeout(1000);
```

### Step 2b: Discovering & Selecting CPE Type Radio

```javascript
const cpeTypes = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="radio"]')) {
      const label = el.nextElementSibling?.textContent?.trim() || '';
      if (label) results.push(label);
    }
  });
  return results;
});

await page.evaluate((targetLabel) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="radio"]')) {
      if ((el.nextElementSibling?.textContent?.trim() || '') === targetLabel) {
        el.click();
      }
    }
  });
}, chosenCPEType);
await page.waitForTimeout(2000);
```

### Step 2c: Discovering & Filling Detail Fields

```javascript
const detailFields = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input, select, textarea')) {
      if (el.tagName === 'INPUT' && ['text', 'number', 'date', 'url'].includes(el.type)) {
        const parentLabel = el.closest('lightning-input')?.getAttribute('label') || '';
        results.push({
          tag: 'INPUT', name: el.name, placeholder: el.placeholder,
          label: parentLabel, type: el.type,
          inputMode: el.inputMode, min: el.min, max: el.max, step: el.step,
          value: el.value
        });
      }
      if (el.tagName === 'SELECT') {
        results.push({
          tag: 'SELECT',
          options: Array.from(el.options).map(o => ({ text: o.text, value: o.value }))
        });
      }
      if (el.tagName === 'TEXTAREA') {
        results.push({ tag: 'TEXTAREA', name: el.name, placeholder: el.placeholder });
      }
    }
  });
  return results;
});

await page.evaluate((fieldValues) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input')) {
      if (el.type !== 'text' && el.type !== 'number' && el.type !== 'url') continue;
      const name = el.name || '';
      if (name in fieldValues.inputs) {
        if (el.inputMode === 'decimal' || el.step) {
          el.value = fieldValues.inputs[name];
        } else {
          const nS = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
          nS.call(el, fieldValues.inputs[name]);
        }
        ['focus', 'input', 'change', 'blur', 'focusout'].forEach(e =>
          el.dispatchEvent(new Event(e, { bubbles: true }))
        );
      }
    }
    for (const el of root.querySelectorAll('select')) {
      const nSS = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
      for (const [matchText, setValue] of Object.entries(fieldValues.selects || {})) {
        if (Array.from(el.options).some(o => o.text.includes(matchText))) {
          const opt = Array.from(el.options).find(o => o.text.includes(matchText));
          if (opt) {
            nSS.call(el, setValue || opt.value);
            el.dispatchEvent(new Event('change', { bubbles: true }));
          }
        }
      }
    }
  });
}, {
  inputs: { Label__c: 'My Title', Publisher__c: 'example.com', Yearpublished__c: '2025', Credits__c: '10' },
  selects: { 'Professional': 'Professional', 'Sole Author': 'Sole Author' }
});

await page.click('button:has-text("Save & Continue")');
await page.waitForURL('**/cpeportaldomainpage', { timeout: 10000 });
```

### Step 3: Discovering & Selecting Domains

```javascript
const domains = await page.evaluate(() => {
  const results = [];
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="checkbox"]')) {
      const label = el.nextElementSibling?.textContent?.trim() || '';
      if (label && el.name === 'domainGroupAOptions') {
        results.push({ label, checked: el.checked });
      }
    }
  });
  return results;
});

await page.evaluate((targetDomains) => {
  walkShadowDOM(document, (root) => {
    for (const el of root.querySelectorAll('input[type="checkbox"]')) {
      const label = el.nextElementSibling?.textContent?.trim() || '';
      if (targetDomains.includes(label) && !el.checked) {
        el.click();
      }
    }
  });
}, ['Cloud Platform & Infrastructure Security']);

await page.click('button:has-text("Save & Continue")');
await page.waitForURL('**/cpeportalreviewpage', { timeout: 10000 });
```

### Step 4: Review & Submit

```javascript
const reviewText = await page.evaluate(() => document.body.innerText);
// Verify dates, title, credits, category, and domain are correct

await page.click('button:has-text("Submit CPE")');
await page.waitForURL('**/cpeportalconfirmationpage', { timeout: 10000 });
```

### Step 5: Submit Another

```javascript
await page.click('button:has-text("Add Another CPE")');
await page.waitForURL('**/s/', { timeout: 10000 });
await page.waitForTimeout(1000);
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
