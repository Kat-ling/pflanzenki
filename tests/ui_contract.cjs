// Executes the real inline UI script against a minimal DOM. No visual test.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

class Element {
    constructor(tag) {
        this.tag = tag; this.children = []; this.handlers = {};
        this.textContent = ''; this.value = ''; this.disabled = false;
        this.className = ''; this.classList = {add: name => {this.className += ' ' + name;}};
    }
    append(...nodes) {for (const node of nodes) this.appendChild(node);}
    appendChild(node) {this.children.push(node); node.parent = this; return node;}
    replaceChildren(...nodes) {this.children = []; this.append(...nodes);}
    addEventListener(name, fn) {this.handlers[name] = fn;}
    remove() {this.parent.children = this.parent.children.filter(node => node !== this);}
    focus() {}
}

(async () => {
    const source = fs.readFileSync(path.join(__dirname, '../app/main.py'), 'utf8');
    const script = source.match(/<script>([\s\S]*?)<\/script>/)[1];
    const elements = new Map();
    const el = id => {
        if (!elements.has(id)) elements.set(id, new Element('div'));
        return elements.get(id);
    };
    const document = {
        getElementById: el, createElement: tag => new Element(tag),
        createTextNode: text => Object.assign(new Element('text'), {textContent: text})
    };
    const requests = [];
    let response;
    const context = vm.createContext({document, console: {error() {}},
        fetch: async (url, request) => {
            requests.push(JSON.parse(request.body));
            return {ok: response.ok !== false, status: response.ok === false ? 502 : 200,
                    json: async () => response.body};
        }
    });
    vm.runInContext(script, context);
    const run = js => vm.runInContext(js, context);
    const ask = async question => {el('question').value = question; await run('askQuestion()');};
    const firstPlan = {intent: 'recommendation', criteria: [{text: 'Freiland'}]};
    response = {body: {intent: 'follow_up', answer: 'Früchte oder Wuchshöhe?', plan: firstPlan,
        recommendations: [], criteria: [{text: 'Freiland', importance: 'required'}]}};
    await ask('Freilandtomate, groß');
    assert.match(el('question-label').textContent, /Antwort auf die Rückfrage/);
    assert.equal(run('history.length'), 2);
    const full = 'Große Früchte.\nNur bedingt für Freiland geeignet. ' + 'Weitere Angaben. '.repeat(40);
    const cards = [1, 2, 3, 4].map(i => ({plant_id: 'id-' + i, plant_name: 'Sorte ' + i, description: full,
        image_filenames: [], reasons: [], checks: [], catalogue_fields: {Beschreibung: full}}));
    const secondPlan = {intent: 'recommendation', criteria: [{text: 'Freiland und groß'}]};
    response = {body: {intent: 'recommendation', answer: 'Testantwort', plan: secondPlan, recommendations: cards,
        criteria: [{text: 'Freiland', importance: 'required'}, {text: 'Große Früchte', importance: 'required'}]}};
    await ask('Ich meine die Früchte');
    assert.equal(requests[1].history.length, 2);
    assert.deepEqual(requests[1].previous_plan, firstPlan);
    assert.equal(requests[1].history[0].content, 'Freilandtomate, groß');
    assert.match(requests[1].history[1].content, /Früchte oder Wuchshöhe/);
    const section = el('result').children.find(node => node.className === 'recommendations');
    assert.equal(section.children.length, 3);
    const content = section.children[0].children.find(node => node.className === 'plant-content');
    assert.equal(content.children.find(node => node.tag === 'p').textContent, full);
    const more = el('result').children.find(node => node.tag === 'button');
    more.handlers.click();
    assert.equal(section.children.length, 4);
    assert.equal(more.hidden, true);
    response = {ok: false, body: {detail: 'Testfehler'}};
    await ask('Was ist mit der zweiten?');
    assert.equal(run('history.length'), 4);
    assert.equal(el('question').value, 'Was ist mit der zweiten?');
    assert.equal(section.children.length, 4);
    assert.match(requests[2].history[3].content, /Sorte 1, Sorte 2, Sorte 3, Sorte 4/);
    assert.deepEqual(requests[2].visible_plant_ids, ['id-1', 'id-2', 'id-3', 'id-4']);
    assert.deepEqual(requests[2].previous_plan, secondPlan);
    assert.equal(JSON.stringify(run('previousPlan')), JSON.stringify(secondPlan));
    assert.equal(el('ask-button').disabled, false);
    el('reset-button').handlers.click();
    assert.equal(run('history.length'), 0);
    assert.equal(el('conversation').children.length, 0);
    response = {body: {intent: 'catalog', answer: 'Gurken', recommendations: []}};
    await ask('Jetzt Gurken');
    assert.deepEqual(requests[3].history, []);
    assert.equal(requests[3].previous_plan, null);
    assert.deepEqual(requests[3].visible_plant_ids, []);
    run('history = Array(40).fill({role: "user", content: "x"})');
    const before = requests.length;
    await ask('Noch eine Frage');
    assert.equal(requests.length, before);
    assert.match(el('status').textContent, /kein Verlauf.*abgeschnitten/);
    console.log('UI contract passed: follow-up, complete context, original text, pagination, failure recovery, reset, history limit.');
})().catch(error => {console.error(error); process.exitCode = 1;});
