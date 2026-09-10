// Optional local browser test. Requires Playwright + Chromium, not a live API key.
// Start the app on port 8765, then: node tests/ui_smoke.cjs
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
    const browser = await chromium.launch({headless: true,
        ...(process.env.PFLANZENKI_CHROMIUM_PATH ? {executablePath: process.env.PFLANZENKI_CHROMIUM_PATH} : {})});
    try {
        const page = await browser.newPage({viewport: {width: 1100, height: 900}});
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const plants = JSON.parse(fs.readFileSync(path.join(__dirname, '../data/normalized/plants.json'), 'utf8'));
        const selected = plants.filter(p => p.image_filenames.length).slice(0, 4);
        const cards = selected.map(p => ({
            plant_id: p.id, plant_name: p.name, plant_category: p.category,
            description: p.description, image_filenames: p.image_filenames,
            reasons: [], checks: [{criterion: 'Testkriterium', importance: 'required',
                kind: 'condition', status: 'yes',
                expression_result: {text: 'Freiland ODER Topf', status: 'yes',
                    children: [{text: 'Freiland', status: 'yes', children: []},
                               {text: 'Topf', status: 'unknown', children: []}]},
                sources: [{field: 'Beschreibung', text: p.description}]}],
            catalogue_fields: {Beschreibung: p.description}
        }));
        const requests = [];
        const state = {intent: 'recommendation', criteria: [{text: 'Freiland'}]};
        await page.route('**/api/ask', async route => {
            requests.push(route.request().postDataJSON());
            if (requests.length === 3) {
                await route.fulfill({status: 502, json: {detail: 'Testfehler: erneut versuchen'}});
                return;
            }
            const follow = requests.length === 1;
            await route.fulfill({json: {
                intent: follow ? 'follow_up' : 'recommendation',
                plan: state,
                answer: follow ? 'Meinst du große Früchte oder eine hohe Pflanze?' : 'Vier Testtreffer.',
                criteria: [{text: 'Freiland', importance: 'required'}],
                recommendations: follow ? [] : cards, unknown: [], excluded: [], warnings: []
            }});
        });
        await page.goto(process.env.PFLANZENKI_TEST_URL || 'http://127.0.0.1:8765');
        await page.locator('#question').fill('Tomate für Freiland und groß');
        await page.locator('#ask-button').click();
        await page.waitForFunction(() => document.querySelector('#question-label').textContent.includes('Rückfrage'));
        assert.equal(await page.locator('#conversation .chat-message').count(), 2);
        await page.locator('#question').fill('Ich meine die Früchte');
        await page.locator('#question').press('Enter');
        await page.waitForFunction(() => document.querySelectorAll('.plant-card').length === 3);
        assert.equal(requests[1].history.length, 2);
        assert.deepEqual(requests[1].previous_plan, state);
        assert.equal(requests[1].history[0].content, 'Tomate für Freiland und groß');
        assert.match(requests[1].history[1].content, /große Früchte/);
        assert.equal(await page.locator('.plant-card .plant-content > p').nth(1).textContent(), selected[0].description);
        await page.getByRole('button', {name: 'Weitere anzeigen (1)'}).click();
        assert.equal(await page.locator('.plant-card').count(), 4);
        await page.getByText('Vollständiger Beleg: Beschreibung', {exact: true}).first().click();
        assert.equal(await page.locator('.criterion-check details').nth(1).locator('.quote').textContent(), selected[0].description);
        await page.getByText('Prüfung der Kombination', {exact: true}).first().click();
        assert.match(await page.locator('.criterion-check details').first().textContent(), /Topf — Woas I ned\./);
        await page.locator('.plant-image').first().evaluate(image => image.decode());
        assert.equal(await page.locator('.plant-image').first().evaluate(img => getComputedStyle(img).objectFit), 'contain');
        if (process.env.PFLANZENKI_UI_ARTIFACTS) {
            fs.mkdirSync(process.env.PFLANZENKI_UI_ARTIFACTS, {recursive: true});
            await page.screenshot({path: path.join(process.env.PFLANZENKI_UI_ARTIFACTS, 'desktop.png'), fullPage: true});
        }
        await page.setViewportSize({width: 390, height: 844});
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
        if (process.env.PFLANZENKI_UI_ARTIFACTS) {
            await page.screenshot({path: path.join(process.env.PFLANZENKI_UI_ARTIFACTS, 'mobile.png'), fullPage: true});
        }
        await page.locator('#question').fill('Und die zweite?');
        await page.locator('#ask-button').click();
        await page.waitForSelector('.error');
        assert.match(requests[2].history[3].content, new RegExp(selected[1].name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
        assert.deepEqual(requests[2].visible_plant_ids, selected.map(p => p.id));
        assert.equal(await page.locator('.plant-card').count(), 4);
        assert.equal(await page.locator('#question').inputValue(), 'Und die zweite?');
        await page.locator('#reset-button').click();
        assert.equal(await page.locator('#conversation .chat-message').count(), 0);
        await page.locator('#question').fill('Jetzt Gurken');
        await page.locator('#ask-button').click();
        await page.waitForFunction(() => document.querySelectorAll('.plant-card').length === 3);
        assert.deepEqual(requests[3].history, []);
        assert.equal(requests[3].previous_plan, null);
        assert.deepEqual(requests[3].visible_plant_ids, []);
        assert.deepEqual(errors, []);
        console.log('Browser checks passed: conversation, follow-up, full text, pagination, images, mobile, error recovery, reset.');
    } finally {
        await browser.close();
    }
})().catch(error => {console.error(error); process.exitCode = 1;});
