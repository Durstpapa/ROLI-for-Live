const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const vm = require("node:vm");

const source = readFileSync(join(__dirname, "../m4l/ROLI-Controls.js"), "utf8");

function setup({ retainRemovedIds = false, sliderRange = 100 } = {}) {
    const outputs = [];
    const logs = [];
    const writes = [];
    const commands = [];
    const tasks = [];
    const sliders = Object.fromEntries(["global_brightness", "background_intensity"].map(name => [
        name, {
            value: 0,
            getvalueof() { return this.value; },
            message(message, value) {
                assert.equal(message, "set", "native range validation must not output");
                this.value = Math.max(0, Math.min(sliderRange, value));
            }
        }
    ]));
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
            if (name === "get_roli_controls_state_v6") {
                if (this.target.error) throw new Error(this.target.error);
                if (this.target.reply) return this.target.reply;
                return ["roli_controls_v6", this.target.white ?? (this.target.colors === "white" ? 1 : 0), this.target.scale ?? 1,
                    this.target.notes ?? 1, this.target.root ?? 1, this.target.clip ?? 0,
                    this.target.ready, this.target.settingsOk === false ? 0 : 1,
                    this.target.source ?? (this.target.clip ? "clip" : "live"),
                    this.target.brightness ?? 100, this.target.background ?? 100,
                    this.target.colors ?? (this.target.white ? "white" : "track")];
            }
            const fields = {
                set_roli_key_colors: "colors",
                set_roli_scale_lighting: "scale",
                set_roli_playing_notes: "notes",
                set_roli_root_color: "root",
                set_roli_clip_scale: "clip",
                set_roli_global_brightness: "brightness",
                set_roli_background_intensity: "background"
            };
            assert.ok(fields[name], "only known settings may be written");
            writes.push(value);
            commands.push([name, value]);
            if (this.target.failSave) {
                this.target.settingsOk = false;
            } else if (!this.target.reject) {
                this.target[fields[name]] = name === "set_roli_key_colors" ?
                    ["white", "track", "rainbow"][value] : value;
                if (name === "set_roli_key_colors") {
                    this.target.white = value === 0 ? 1 : 0;
                }
                this.target.settingsOk = true;
            }
            return this.call("get_roli_controls_state_v6");
        }
    }
    class Task {
        constructor(fn) { this.fn = fn; tasks.push(this); }
        cancel() { this.cancelled = true; }
        repeat() { this.repeating = true; }
        schedule(delay) { this.delay = delay; this.scheduled = true; }
    }
    const context = vm.createContext({
        LiveAPI, Task, inlet: 0,
        patcher: { getnamed: name => sliders[name] },
        outlet: (...args) => outputs.push(args),
        post: text => logs.push(text)
    });
    vm.runInContext(source, context);
    return {
        context, outputs, logs, writes, commands, tasks,
        surfaces: value => { surfaces = value; },
        click(index = 1) { context.inlet = index; context.bang(); },
        level(index, value) { context.inlet = index; context.msg_float(value); },
        flush() {
            for (const task of tasks.filter(t => t.scheduled && !t.cancelled)) {
                task.scheduled = false;
                task.fn();
            }
        },
        status() { return outputs.filter(o => o[0] === 5 && o[1] === "set").at(-1)?.[2]; },
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

test("connection dot follows confirmed readiness without hiding status or clip-source errors", () => {
    const h = setup();
    const surface = { id: 7, ready: 0, clip: 1, source: "idle" };
    const dot = () => h.outputs.filter(o => o[0] === 8 && o[1] === "set").at(-1)?.[2];
    h.surfaces([surface]);
    assert.equal(dot(), undefined, "no connection is claimed before Live API initialization");
    h.context.bang();
    assert.equal(dot(), 0);
    assert.equal(h.status(), "Disconnected");
    surface.ready = 1;
    h.context.refresh();
    assert.equal(dot(), 1);
    assert.equal(h.status(), "Connected\nUsing Live scale\nNo playing clip");
    for (const source of ["unsupported", "error"]) {
        surface.source = source;
        h.context.refresh();
        assert.equal(dot(), 1, "clip fallback does not imply disconnection");
        assert.match(h.status(), /Connected\nClip scale (unavailable|read error)\nUsing Live scale/);
    }
    surface.settingsOk = false;
    h.context.refresh();
    assert.equal(dot(), 1, "a settings-file error does not imply disconnection");
    assert.match(h.status(), /Settings file error/);
    surface.error = "Live API unavailable";
    h.context.refresh();
    assert.equal(dot(), 0, "a stale connection must not stay accented after API failure");
    assert.equal(h.status(), "Live API unavailable");
    delete surface.error;
    surface.settingsOk = true;
    surface.source = "clip";
    h.context.refresh();
    assert.equal(dot(), 1);
    assert.equal(h.status(), "Connected\nPlaying clip scale");
    h.surfaces([]);
    h.context.refresh();
    assert.equal(dot(), 0);
    assert.equal(h.status(), "Disconnected");
    assert.deepEqual(h.writes, [], "connection feedback must never change saved settings");
});

test("Rainbow displays confirmed state, disables custom lighting controls, and restores them on White", () => {
    const h = setup();
    const surface = { id: 7, colors: "rainbow", ready: 1, clip: 1, root: 0, background: 25 };
    h.surfaces([surface]);
    h.context.bang();
    assert.equal(h.label(), "Key colors: Rainbow");
    assert.equal(h.status(), "Connected\nPlaying clip scale");
    assert.equal(h.label(3), "Root color: OFF");
    assert.equal(h.label(4), "Follow clip scale: ON");
    for (const [index, active] of [[0, 1], [1, 1], [2, 1], [3, 0], [4, 1], [6, 1], [7, 0]]) {
        assert.deepEqual(h.outputs.filter(o => o[0] === index && o[1] === "active").at(-1),
            [index, "active", active]);
    }
    assert.deepEqual(h.writes, [], "loading Rainbow must not apply defaults");
    h.level(6, 70);
    h.flush();
    assert.deepEqual(h.commands, [["set_roli_global_brightness", 70]]);
    h.click();
    assert.equal(h.label(), "Key colors: White");
    for (const index of [3, 4, 7]) {
        assert.deepEqual(h.outputs.filter(o => o[0] === index && o[1] === "active").at(-1),
            [index, "active", 1]);
    }
    assert.equal(surface.clip, 1);
    assert.equal(surface.root, 0);
    assert.equal(surface.background, 25);
});

test("Rainbow choice survives scale lighting off and on", () => {
    const h = setup();
    h.surfaces([{ id: 7, colors: "rainbow", ready: 1 }]);
    h.context.bang();
    h.click(2);
    assert.equal(h.label(), "Key colors: Rainbow");
    assert.match(h.status(), /Native colors restored/);
    h.click(2);
    assert.equal(h.status(), "Connected");
    assert.deepEqual(h.commands, [["set_roli_scale_lighting", 0], ["set_roli_scale_lighting", 1]]);
});

test("a deferred background write cannot change saved preferences after switching to Rainbow", () => {
    const h = setup();
    const surface = { id: 7, white: 1, ready: 1, background: 25 };
    h.surfaces([surface]);
    h.context.bang();
    h.level(7, 60);
    surface.colors = "rainbow";
    h.flush();
    assert.match(h.status(), /Background control unavailable/);
    assert.equal(surface.background, 25);
    assert.deepEqual(h.writes, []);
});

test("Rainbow rejects stale root-color events but allows Clip scale changes", () => {
    const h = setup();
    h.surfaces([{ id: 7, colors: "rainbow", ready: 1, root: 1, clip: 0 }]);
    h.context.bang();
    h.click(4);
    assert.match(h.status(), /Control unavailable/);
    assert.deepEqual(h.writes, []);
    h.context.refresh();
    h.click(5);
    assert.equal(h.label(4), "Follow clip scale: ON");
    assert.equal(h.status(), "Connected\nPlaying clip scale");
    assert.deepEqual(h.commands, [["set_roli_clip_scale", 1]]);
});

test("Rainbow still reports clip-scale fallback and read failures", () => {
    for (const [source, message] of [["unsupported", /Clip scale unavailable/], ["error", /Clip scale read error/]]) {
        const h = setup();
        h.surfaces([{ id: 7, colors: "rainbow", ready: 1, clip: 1, source }]);
        h.context.bang();
        assert.match(h.status(), message);
        assert.deepEqual(h.writes, []);
    }
});

test("repeated identical button clicks cycle Track, Rainbow, White from confirmed script state", () => {
    const h = setup();
    h.context.bang();
    h.click();
    assert.deepEqual(h.writes, [2]);
    assert.equal(h.label(), "Key colors: Rainbow");
    assert.deepEqual(h.outputs.filter(o => o[0] === 0 && o[1] === "text").at(-1), [0, "text", "Key colors: Rainbow"]);
    h.context.refresh();
    h.click();
    assert.equal(h.label(), "Key colors: White");
    assert.deepEqual(h.writes, [2, 0]);
    for (let i = 0; i < 6; i++) {
        h.context.refresh();
        h.click();
    }
    assert.deepEqual(h.writes, [2, 0, 1, 2, 0, 1, 2, 0]);
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
    assert.deepEqual(h.writes, [1]);
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
    for (let index = 0; index < 5; index++) {
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
    for (let index = 0; index < 5; index++) {
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
    h.surfaces([{ id: 1, type: "ControlSurface", info: "function get_roli_controls_state_v6", white: 0, ready: 1 }]);
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
    assert.equal(h.label(2), "Show playing notes: OFF");
    assert.equal(h.label(3), "Root color: OFF");
    surface.ready = 1;
    h.tasks[0].fn();
    assert.equal(h.status(), "Connected");
    assert.deepEqual(h.writes, []);
});

test("invalid or old script replies fail explicitly before any write", () => {
    for (const reply of [
        ["roli_controls_v2", 0, 1, 1, 1, 1], ["roli_controls_v3", 1, 1, 1, 1, 1, 1],
        ["roli_controls_v4", 2, 1, 1, 1, 0, 1, 1, "live"],
        ["roli_controls_v4", 1, 1, 1, 1, 0, 1, 1, "unknown"],
        ["roli_controls_v5", 1, 1, 1, 1, 0, 1, 1, "live", 101, 25],
        ["roli_controls_v5", 1, 1, 1, 1, 0, 1, 1, "live", 100, -1],
        ["roli_controls_v6", 1, 1, 1, 1, 0, 1, 1, "live", 101, 25, "white"],
        ["roli_controls_v6", 1, 1, 1, 1, 0, 1, 1, "live", 100, -1, "white"],
        ["roli_controls_v6", 1, 1, 1, 1, 0, 1, 1, "live", 100, 25, "invalid"]
    ]) {
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
    for (let index = 0; index < 5; index++) {
        assert.deepEqual(h.outputs.filter(o => o[0] === index && o[1] === "active").at(-1), [index, "active", 0]);
    }
});

test("a click inverts externally changed state, even before the next poll", () => {
    const h = setup();
    h.context.bang();
    h.surfaces([{ id: 8, white: 1, ready: 1 }]);
    h.click();
    assert.deepEqual(h.writes, [1]);
    assert.equal(h.label(), "Key colors: Track");
});

test("scale and playing-note switches are independent and preserve the saved color mode", () => {
    const h = setup();
    h.context.bang();
    h.click(2);
    assert.equal(h.label(1), "Scale lighting: OFF");
    assert.equal(h.label(2), "Show playing notes: ON");
    assert.equal(h.label(), "Key colors: Track");
    assert.deepEqual(h.outputs.filter(o => o[0] === 0 && o[1] === "active").at(-1), [0, "active", 0]);
    assert.match(h.status(), /Native colors restored/);
    h.click(3);
    assert.equal(h.label(2), "Show playing notes: OFF");
    assert.equal(h.label(1), "Scale lighting: OFF");
    h.click(2);
    assert.equal(h.label(1), "Scale lighting: ON");
    assert.equal(h.label(2), "Show playing notes: OFF");
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
    assert.equal(h.label(2), "Show playing notes: OFF");
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
    assert.equal(h.label(2), "Show playing notes: ON");
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

test("clip-scale control alternates confirmed state independently and never writes on load", () => {
    const h = setup();
    h.context.bang();
    assert.equal(h.label(4), "Follow clip scale: OFF");
    assert.deepEqual(h.writes, []);
    h.click(5);
    assert.equal(h.label(4), "Follow clip scale: ON");
    assert.equal(h.status(), "Connected\nPlaying clip scale");
    assert.equal(h.label(2), "Show playing notes: ON");
    h.click(5);
    assert.equal(h.label(4), "Follow clip scale: OFF");
    assert.equal(h.status(), "Connected");
    assert.deepEqual(h.commands, [["set_roli_clip_scale", 1], ["set_roli_clip_scale", 0]]);
    assert.equal(h.tasks.length, 1);
});

test("clip-scale source and fallback messages remain explicit and recover automatically", () => {
    const h = setup();
    const surface = { id: 7, white: 1, clip: 1, ready: 1, source: "idle" };
    h.surfaces([surface]);
    h.context.bang();
    assert.equal(h.label(4), "Follow clip scale: ON");
    assert.equal(h.status(), "Connected\nUsing Live scale\nNo playing clip");
    for (const [source, label] of [
        ["unsupported", "Clip scale unavailable"], ["error", "Clip scale read error"]
    ]) {
        surface.source = source;
        h.context.refresh();
        assert.equal(h.status(), `Connected\n${label}\nUsing Live scale`);
        const logs = h.logs.length;
        h.context.refresh();
        assert.equal(h.logs.length, logs);
    }
    surface.ready = 0;
    h.context.refresh();
    assert.equal(h.status(), "Disconnected");
    surface.ready = 1;
    surface.source = "clip";
    h.context.refresh();
    assert.equal(h.status(), "Connected\nPlaying clip scale");
    assert.deepEqual(h.writes, []);
});

test("scale lighting off preserves clip source choice while disabling its control", () => {
    const h = setup();
    h.surfaces([{ id: 7, white: 1, scale: 0, clip: 1, ready: 1, source: "off" }]);
    h.context.bang();
    assert.equal(h.label(4), "Follow clip scale: ON");
    assert.deepEqual(h.outputs.filter(o => o[0] === 4 && o[1] === "active").at(-1),
        [4, "active", 0]);
    h.click(2);
    assert.deepEqual(h.outputs.filter(o => o[0] === 4 && o[1] === "active").at(-1),
        [4, "active", 1]);
    assert.equal(h.label(4), "Follow clip scale: ON");
});

test("failed clip setting saves never confirm a successful change", () => {
    const h = setup();
    h.surfaces([{ id: 7, white: 1, ready: 1, failSave: true }]);
    h.context.bang();
    h.click(5);
    assert.match(h.status(), /Settings were not saved/);
    assert.equal(h.label(4), "Follow clip scale: OFF");
    assert.deepEqual(h.commands, [["set_roli_clip_scale", 1]]);
});

test("level controls read confirmed percentages without writing on load or poll", () => {
    const h = setup();
    h.surfaces([{ id: 7, white: 1, ready: 1, brightness: 61, background: 25 }]);
    h.context.bang();
    h.context.refresh();
    assert.deepEqual(h.outputs.filter(o => o[0] === 6 && o[1] === "set").at(-1), [6, "set", 61]);
    assert.deepEqual(h.outputs.filter(o => o[0] === 7 && o[1] === "set").at(-1), [7, "set", 25]);
    assert.deepEqual(h.writes, []);
    assert.deepEqual(h.outputs.filter(o => o[0] === 6 && o[1] === "active").at(-1), [6, "active", 1]);
});

test("startup slider output before live.thisdevice cannot overwrite saved levels", () => {
    const h = setup();
    h.level(6, 0);
    h.level(7, 0);
    h.flush();
    assert.equal(h.tasks.length, 0);
    assert.deepEqual(h.writes, []);
    h.context.bang();
    assert.equal(h.status(), "Connected");
    assert.deepEqual(h.writes, []);
});

test("collapsed native slider range disables controls before any API write or polling", () => {
    const h = setup({ sliderRange: 0 });
    h.context.bang();
    assert.match(h.status(), /Slider range error/);
    assert.equal(h.tasks.length, 0);
    assert.deepEqual(h.writes, []);
    assert.deepEqual(h.outputs.filter(o => o[0] === 6 && o[1] === "active").at(-1), [6, "active", 0]);
    h.level(6, 0);
    h.flush();
    assert.deepEqual(h.writes, []);
});

test("slider drags coalesce to the latest value and use acknowledged integer percentages", () => {
    const h = setup();
    h.context.bang();
    h.level(6, 70);
    h.level(6, 50.4);
    h.level(7, 25);
    assert.deepEqual(h.writes, []);
    const task = h.tasks.find(t => t.scheduled);
    assert.equal(task.delay, 100);
    h.flush();
    assert.deepEqual(h.commands, [["set_roli_global_brightness", 50], ["set_roli_background_intensity", 25]]);
    assert.deepEqual(h.outputs.filter(o => o[0] === 6 && o[1] === "set").at(-1), [6, "set", 50]);
    h.level(6, 50);
    h.flush();
    assert.equal(h.commands.length, 2, "unchanged levels must not repeatedly save preferences");
});

test("global remains active with native colors while background is disabled", () => {
    const h = setup();
    h.surfaces([{ id: 7, white: 1, scale: 0, ready: 1, background: 25, source: "off" }]);
    h.context.bang();
    assert.deepEqual(h.outputs.filter(o => o[0] === 6 && o[1] === "active").at(-1), [6, "active", 1]);
    assert.deepEqual(h.outputs.filter(o => o[0] === 7 && o[1] === "active").at(-1), [7, "active", 0]);
    h.level(6, 40);
    h.flush();
    assert.deepEqual(h.commands, [["set_roli_global_brightness", 40]]);
});

test("unknown hardware brightness is not replaced by the slider's startup value", () => {
    const h = setup();
    h.surfaces([{ id: 7, white: 1, ready: 0, brightness: -1, background: 25 }]);
    h.context.bang();
    assert.deepEqual(h.outputs.filter(o => o[0] === 6 && o[1] === "set"), []);
    assert.deepEqual(h.outputs.filter(o => o[0] === 6 && o[1] === "active").at(-1), [6, "active", 0]);
    h.level(6, 0);
    h.flush();
    assert.equal(h.status(), "Disconnected");
    assert.deepEqual(h.writes, []);
});

test("queued slider writes rediscover the surface and reject removal", () => {
    const h = setup({ retainRemovedIds: true });
    h.context.bang();
    h.level(6, 40);
    h.surfaces([]);
    h.flush();
    assert.equal(h.status(), "Disconnected");
    assert.deepEqual(h.writes, []);
});

test("slider save failures and rejected values never look like acknowledged changes", () => {
    for (const failure of [{ failSave: true }, { reject: true }]) {
        const h = setup();
        h.surfaces([{ id: 7, white: 1, ready: 1, ...failure }]);
        h.context.bang();
        h.level(7, 25);
        h.flush();
        assert.match(h.status(), /not saved|did not accept/);
        assert.deepEqual(h.outputs.filter(o => o[0] === 7 && o[1] === "active").at(-1), [7, "active", 0]);
        assert.deepEqual(h.commands, [["set_roli_background_intensity", 25]]);
    }
});

test("invalid numeric events never queue a slider write", () => {
    const h = setup();
    h.context.bang();
    for (const value of [-1, 101, NaN, Infinity, "25", null]) {
        h.level(6, value);
        assert.match(h.status(), /Invalid brightness input/);
    }
    h.flush();
    assert.deepEqual(h.writes, []);
});

test("deleting the device cancels deferred level writes", () => {
    const h = setup();
    h.context.bang();
    h.level(6, 40);
    const task = h.tasks.find(t => t.scheduled);
    h.context.notifydeleted();
    assert.equal(task.cancelled, true);
    h.flush();
    assert.deepEqual(h.writes, []);
});
