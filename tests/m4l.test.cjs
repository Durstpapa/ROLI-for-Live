const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");

const source = readFileSync(join(__dirname, "../m4l/ROLI-Controls.js"), "utf8");

function setup({ retainRemovedIds = false } = {}) {
    const outputs = [];
    const logs = [];
    const writes = [];
    const commands = [];
    const tasks = [];
    let surfaces = [{ id: 7, white: 0, ready: 1 }];
    class LiveAPI {
        constructor(callback, path) {
            this.path = path;
            this.target = path.startsWith("id ") ?
                surfaces.find(s => s.id === Number(path.slice(3))) : null;
        }
        get id() {
            return this.target && (retainRemovedIds || surfaces.includes(this.target)) ? this.target.id : 0;
        }
        get type() { return this.target?.type || "ROLIForLive"; }
        get info() { return this.target?.info || ""; }
        get(name) {
            assert.equal(this.path, "live_app");
            assert.equal(name, "control_surfaces");
            return surfaces.flatMap(s => ["id", s.id]);
        }
        call(name, value) {
            assert.ok(this.id, "must not call a stale surface");
            if (name === "get_roli_controls_state_v3") {
                if (this.target.error) throw new Error(this.target.error);
                if (this.target.reply) return this.target.reply;
                return ["roli_controls_v3", this.target.white, this.target.scale ?? 1,
                    this.target.notes ?? 1, this.target.root ?? 1, this.target.ready,
                    this.target.settingsOk === false ? 0 : 1];
            }
            const fields = {
                set_roli_white_keys: "white",
                set_roli_scale_lighting: "scale",
                set_roli_playing_notes: "notes",
                set_roli_root_color: "root"
            };
            assert.ok(fields[name], "only known settings may be written");
            writes.push(value);
            commands.push([name, value]);
            if (this.target.failSave) {
                this.target.settingsOk = false;
            } else if (!this.target.reject) {
                this.target[fields[name]] = value;
                this.target.settingsOk = true;
            }
            return this.call("get_roli_controls_state_v3");
        }
    }
    class Task {
        constructor(fn) { this.fn = fn; tasks.push(this); }
        cancel() { this.cancelled = true; }
        repeat() { this.repeating = true; }
    }
    const context = vm.createContext({
        LiveAPI, Task, inlet: 0,
        outlet: (...args) => outputs.push(args),
        post: text => logs.push(text)
    });
    vm.runInContext(source, context);
    return {
        context, outputs, logs, writes, commands, tasks,
        surfaces: value => { surfaces = value; },
        click(index = 1) { context.inlet = index; context.bang(); },
        status() { return outputs.filter(o => o[0] === 4).at(-1)?.[2]; },
        label(index = 0) { return outputs.filter(o => o[0] === index && o[1] === "text").at(-1)?.[2]; }
    };
}

test("waits for live.thisdevice, then reads the script without changing it", () => {
    const h = setup();
    assert.equal(h.outputs.length, 0);
    assert.equal(h.tasks.length, 0);
    h.context.bang();
    assert.equal(h.status(), "Connected");
    assert.equal(h.label(), "Key colors: Track");
    assert.deepEqual(h.writes, []);
    assert.equal(h.tasks[0].interval, 500);
    assert.equal(h.tasks[0].repeating, true);
    assert.deepEqual(h.outputs.find(o => o[1] === "text" && o[0] === 0), [0, "text", "Key colors: Track"]);
});

test("repeated identical button clicks alternate both ways from confirmed script state", () => {
    const h = setup();
    h.context.bang();
    h.click();
    assert.deepEqual(h.writes, [1]);
    assert.equal(h.label(), "Key colors: White");
    assert.deepEqual(h.outputs.filter(o => o[0] === 0 && o[1] === "text").at(-1), [0, "text", "Key colors: White"]);
    h.context.refresh();
    h.click();
    assert.equal(h.label(), "Key colors: Track");
    assert.deepEqual(h.writes, [1, 0]);
    for (let i = 0; i < 6; i++) {
        h.context.refresh();
        h.click();
    }
    assert.deepEqual(h.writes, [1, 0, 1, 0, 1, 0, 1, 0]);
    assert.equal(h.tasks.length, 1, "clicks must not restart the polling task");
});

test("white-keys startup default is displayed without a write and the first click turns it off", () => {
    const h = setup();
    h.surfaces([{ id: 7, white: 1, ready: 1 }]);
    h.context.bang();
    assert.deepEqual(h.writes, []);
    assert.deepEqual(h.outputs.find(o => o[0] === 0 && o[1] === "text"),
        [0, "text", "Key colors: White"]);
    assert.equal(h.status(), "Connected");
    h.click();
    assert.deepEqual(h.writes, [0]);
    assert.equal(h.label(), "Key colors: Track");
});

test("polling follows changes from another device without writing", () => {
    const h = setup();
    h.context.bang();
    h.surfaces([{ id: 8, white: 1, ready: 1 }]);
    h.tasks[0].fn();
    assert.equal(h.label(), "Key colors: White");
    assert.deepEqual(h.writes, []);
});

test("missing connection shows neutral status and reconnects automatically", () => {
    const h = setup();
    h.surfaces([]);
    h.context.bang();
    assert.equal(h.status(), "Disconnected");
    for (let index = 0; index < 4; index++) {
        assert.deepEqual(h.outputs.filter(o => o[0] === index && o[1] === "active").at(-1), [index, "active", 0]);
    }
    h.context.refresh();
    assert.equal(h.logs.length, 1, "repeated failures should not flood the console");
    h.surfaces([{ id: 11, white: 1, ready: 1 }]);
    h.tasks[0].fn();
    assert.equal(h.status(), "Connected");
    assert.equal(h.label(), "Key colors: White");
    assert.equal(h.tasks.length, 1, "reconnection must not require reloading the device");
    assert.deepEqual(h.writes, [], "automatic connection must not change preferences");
    for (let index = 0; index < 4; index++) {
        assert.deepEqual(h.outputs.filter(o => o[0] === index && o[1] === "active").at(-1), [index, "active", 1]);
    }
});

test("does not select an unrelated control surface", () => {
    const h = setup();
    h.surfaces([{ id: 1, type: "Push", info: "function get_control_names", error: "wrong surface" }]);
    h.context.bang();
    assert.equal(h.status(), "Disconnected");
    assert.deepEqual(h.writes, []);
});

test("polling rejects a removed surface even when its old API object retains a valid ID", () => {
    const h = setup({ retainRemovedIds: true });
    h.context.bang();
    assert.equal(h.status(), "Connected");
    h.surfaces([]);
    h.tasks[0].fn();
    assert.equal(h.status(), "Disconnected");
    h.surfaces([{ id: 18, white: 1, ready: 1 }]);
    h.tasks[0].fn();
    assert.equal(h.status(), "Connected");
    assert.equal(h.label(), "Key colors: White");
    assert.deepEqual(h.writes, []);
});

test("accepts a generic ControlSurface only when its API advertises the bridge", () => {
    const h = setup();
    h.surfaces([{ id: 1, type: "ControlSurface", info: "function get_roli_controls_state_v3", white: 0, ready: 1 }]);
    h.context.bang();
    assert.equal(h.status(), "Connected");
});

test("multiple ROLI surfaces are ambiguous and never written", () => {
    const h = setup();
    h.surfaces([{ id: 1 }, { id: 2 }]);
    h.context.bang();
    h.click();
    assert.match(h.status(), /Enable only one/);
    assert.deepEqual(h.writes, []);
});

test("keyboard waiting is distinct from a ready script", () => {
    const h = setup();
    h.surfaces([{ id: 7, white: 0, ready: 0 }]);
    h.context.bang();
    assert.equal(h.status(), "Disconnected");
});

test("power-off and reconnection update status on the same live script without changing preferences", () => {
    const h = setup();
    const surface = { id: 7, white: 1, scale: 1, notes: 0, root: 0, ready: 1 };
    h.surfaces([surface]);
    h.context.bang();
    assert.equal(h.status(), "Connected");
    surface.ready = 0;
    h.tasks[0].fn();
    assert.equal(h.status(), "Disconnected");
    assert.equal(h.label(2), "Playing notes: OFF");
    assert.equal(h.label(3), "Root color: OFF");
    surface.ready = 1;
    h.tasks[0].fn();
    assert.equal(h.status(), "Connected");
    assert.deepEqual(h.writes, []);
});

test("invalid or old script replies fail explicitly before any write", () => {
    for (const reply of [["roli_controls_v2", 0, 1, 1, 1, 1], ["roli_controls_v3", 2, 1, 1, 1, 1, 1]]) {
        const h = setup();
        h.surfaces([{ id: 7, reply }]);
        h.click();
        assert.match(h.status(), /Update ROLI script: unexpected reply/);
        assert.deepEqual(h.writes, []);
    }
});

test("API failures and rejected settings never report success", () => {
    const h = setup();
    h.surfaces([{ id: 7, error: "Live API unavailable" }]);
    h.context.bang();
    assert.equal(h.status(), "Live API unavailable");
    h.surfaces([{ id: 8, white: 0, ready: 1, reject: true }]);
    h.click();
    assert.match(h.status(), /did not accept/);
    for (let index = 0; index < 4; index++) {
        assert.deepEqual(h.outputs.filter(o => o[0] === index && o[1] === "active").at(-1), [index, "active", 0]);
    }
});

test("a click inverts externally changed state, even before the next poll", () => {
    const h = setup();
    h.context.bang();
    h.surfaces([{ id: 8, white: 1, ready: 1 }]);
    h.click();
    assert.deepEqual(h.writes, [0]);
    assert.equal(h.label(), "Key colors: Track");
});

test("scale and playing-note switches are independent and preserve the saved color mode", () => {
    const h = setup();
    h.context.bang();
    h.click(2);
    assert.equal(h.label(1), "Scale lighting: OFF");
    assert.equal(h.label(2), "Playing notes: ON");
    assert.equal(h.label(), "Key colors: Track");
    assert.deepEqual(h.outputs.filter(o => o[0] === 0 && o[1] === "active").at(-1), [0, "active", 0]);
    assert.match(h.status(), /ROLI lighting restored/);
    h.click(3);
    assert.equal(h.label(2), "Playing notes: OFF");
    assert.equal(h.label(1), "Scale lighting: OFF");
    h.click(2);
    assert.equal(h.label(1), "Scale lighting: ON");
    assert.equal(h.label(2), "Playing notes: OFF");
    assert.equal(h.label(), "Key colors: Track");
    assert.deepEqual(h.commands, [
        ["set_roli_scale_lighting", 0], ["set_roli_playing_notes", 0], ["set_roli_scale_lighting", 1]
    ]);
});

test("loading saved settings never writes defaults back to the script", () => {
    const h = setup();
    h.surfaces([{ id: 7, white: 0, scale: 0, notes: 0, root: 0, ready: 1 }]);
    h.context.bang();
    assert.equal(h.label(), "Key colors: Track");
    assert.equal(h.label(1), "Scale lighting: OFF");
    assert.equal(h.label(2), "Playing notes: OFF");
    assert.equal(h.label(3), "Root color: OFF");
    assert.deepEqual(h.writes, []);
});

test("root-color clicks alternate independently and the control follows scale-lighting availability", () => {
    const h = setup();
    h.context.bang();
    assert.equal(h.label(3), "Root color: ON");
    h.click(4);
    assert.equal(h.label(3), "Root color: OFF");
    h.context.refresh();
    h.click(4);
    assert.equal(h.label(3), "Root color: ON");
    assert.deepEqual(h.commands, [["set_roli_root_color", 0], ["set_roli_root_color", 1]]);
    h.click(2);
    assert.equal(h.label(3), "Root color: ON", "retain the saved choice while native lighting is restored");
    assert.deepEqual(h.outputs.filter(o => o[0] === 3 && o[1] === "active").at(-1), [3, "active", 0]);
    assert.equal(h.label(2), "Playing notes: ON");
    h.click(2);
    assert.deepEqual(h.outputs.filter(o => o[0] === 3 && o[1] === "active").at(-1), [3, "active", 1]);
});

test("settings load and save failures stay visible and cannot look like a successful toggle", () => {
    const h = setup();
    h.surfaces([{ id: 7, white: 1, ready: 1, settingsOk: false, failSave: true }]);
    h.context.bang();
    assert.match(h.status(), /Settings file error/);
    h.click();
    assert.match(h.status(), /Settings were not saved/);
    assert.equal(h.label(), "Key colors: White");
    h.context.refresh();
    assert.match(h.status(), /Settings file error/);
    h.surfaces([{ id: 8, white: 1, ready: 1 }]);
    h.click();
    assert.equal(h.label(), "Key colors: Track");
    assert.equal(h.status(), "Connected");
});

test("reinitialization and deletion cancel polling", () => {
    const h = setup();
    h.context.bang();
    h.context.bang();
    assert.equal(h.tasks.length, 2);
    assert.equal(h.tasks[0].cancelled, true);
    h.context.notifydeleted();
    assert.equal(h.tasks[1].cancelled, true);
});
