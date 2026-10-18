import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { build, outputDir } from "../m4l/build.mjs";

test("generated audio effect embeds JS, passes stereo audio directly, and wires confirmed UI state", async () => {
    const patch = await build();
    const p = patch.patcher;
    const boxes = p.boxes.map(({ box }) => box);
    const script = boxes.find(b => b.text === "v8");
    const audioIn = boxes.find(b => b.text === "plugin~");
    const audioOut = boxes.find(b => b.text === "plugout~");
    const toggle = boxes.find(b => b.varname === "white_keys");
    const init = boxes.find(b => b.text === "live.thisdevice");
    const edges = p.lines.map(({ patchline: l }) => [...l.source, ...l.destination]);
    const hasEdge = (from, outlet, to, inlet) =>
        edges.some(e => JSON.stringify(e) === JSON.stringify([from, outlet, to, inlet]));
    assert.equal(script.textfile.embed, 1);
    assert.match(script.textfile.text, /function readState/);
    assert.equal(p.openinpresentation, 1);
    assert.equal(p.devicewidth, 240, "two level sliders sit beside the unchanged button stack");
    assert.equal(p.saved_attribute_attributes.bgcolor.expression, "themecolor.live_surface_bg");
    assert.equal(toggle.saved_attribute_attributes.activebgcolor.expression, "themecolor.live_control_bg");
    assert.equal(toggle.saved_attribute_attributes.focusbordercolor.expression, "themecolor.live_focus_frame");
    const visible = boxes.filter(b => b.presentation === 1);
    assert.equal(visible.length, 10, "five buttons, status, two sliders and their labels");
    assert.deepEqual(
        visible.filter(b => b.maxclass === "live.text")
            .sort((a, b) => a.presentation_rect[1] - b.presentation_rect[1])
            .map(b => b.varname),
        ["scale_lighting", "white_keys", "root_color", "playing_notes", "clip_scale"],
        "requested top-to-bottom order must not change inlet/outlet semantics");
    assert.ok(!visible.some(b => /proof of concept|js2max|Live color switch/i.test(b.text)));
    for (const box of visible) {
        const [x, y, width, height] = box.presentation_rect;
        assert.ok(x >= 0 && y >= 0 && x + width <= 240 && y + height <= 169,
            "all presentation content fits the compact device strip");
        assert.ok(box.fontsize >= 10 && box.fontsize <= 11, "stock-sized, readable text");
        if (box.maxclass === "comment") {
            assert.equal(box.saved_attribute_attributes.textcolor.expression, "themecolor.live_control_fg");
        }
    }
    for (let i = 0; i < visible.length; i++) {
        for (let j = i + 1; j < visible.length; j++) {
            const [ax, ay, aw, ah] = visible[i].presentation_rect;
            const [bx, by, bw, bh] = visible[j].presentation_rect;
            assert.ok(ax + aw <= bx || bx + bw <= ax || ay + ah <= by || by + bh <= ay,
                "visible controls and status must not overlap");
        }
    }
    assert.equal(toggle.active, 0, "must wait for script confirmation");
    assert.equal(toggle.mode, 0, "momentary clicks must invert script state, not widget state");
    assert.equal(toggle.parameter_enable, 0, "POC must not restore a stale saved preference");
    assert.ok(toggle.presentation_rect[2] >= 24 && toggle.presentation_rect[3] >= 24);
    assert.ok(!boxes.some(b => b.text === "midiin" || b.text === "midiout"));
    assert.equal(audioIn.numoutlets, 2);
    assert.deepEqual(audioIn.outlettype, ["signal", "signal"]);
    assert.equal(audioOut.numinlets, 2);
    assert.ok(hasEdge(audioIn.id, 0, audioOut.id, 0), "left audio passes through unchanged");
    assert.ok(hasEdge(audioIn.id, 1, audioOut.id, 1), "right audio passes through unchanged");
    assert.ok(hasEdge(init.id, 0, script.id, 0));
    assert.ok(hasEdge(toggle.id, 0, script.id, 1));
    assert.ok(hasEdge(script.id, 0, toggle.id, 0));
    assert.equal(script.numinlets, 8);
    assert.equal(script.numoutlets, 8);
    for (const [index, name] of ["white_keys", "scale_lighting", "playing_notes", "root_color", "clip_scale"].entries()) {
        const control = boxes.find(b => b.varname === name);
        assert.ok(hasEdge(control.id, 0, script.id, index + 1));
        assert.ok(hasEdge(script.id, index, control.id, 0));
        assert.equal(control.mode, 0);
        assert.equal(control.active, 0);
        assert.equal(control.parameter_enable, 0);
        assert.ok(control.presentation_rect[2] >= 24 && control.presentation_rect[3] >= 24);
    }
    assert.ok(hasEdge(script.id, 5, "roli-status", 0));
    for (const [index, name] of ["global_brightness", "background_intensity"].entries()) {
        const slider = boxes.find(b => b.varname === name);
        const label = boxes.find(b => b.id === `label-${name}`);
        assert.equal(label.text, index === 0 ? "Global\nBrightness (%)" : "Background\nBrightness (%)");
        assert.equal(label.linecount, 2);
        assert.equal(slider.maxclass, "live.slider");
        assert.equal(slider.orientation, 1);
        assert.equal(slider.parameter_enable, 1, "native parameter engine owns the numeric range");
        assert.equal(slider.saved_object_attributes.parameter_enable, 1);
        assert.equal(slider.active, 0);
        assert.equal(slider.saved_attribute_attributes.valueof.parameter_type, 1);
        assert.equal(slider.saved_attribute_attributes.valueof.parameter_mmin, 0);
        assert.equal(slider.saved_attribute_attributes.valueof.parameter_mmax, 100);
        assert.deepEqual(slider.saved_attribute_attributes.valueof.parameter_initial,
            [index === 0 ? 100 : 25], "native double-click resets to the chosen brightness");
        assert.equal(slider.saved_attribute_attributes.valueof.parameter_initial_enable, 0);
        assert.equal(slider.saved_attribute_attributes.valueof.parameter_invisible, 2);
        assert.ok(slider.presentation_rect[2] >= 24 && slider.presentation_rect[3] >= 24);
        assert.ok(hasEdge(slider.id, 0, script.id, index + 6));
        assert.ok(hasEdge(script.id, index + 6, slider.id, 0));
    }
    assert.equal(edges.filter(e => e[0] === audioIn.id).length, 2, "no audio processing or extra signal paths");
    assert.equal(edges.filter(e => e[2] === audioOut.id).length, 2, "no mixed or generated audio");
    for (const e of edges) {
        const from = boxes.find(b => b.id === e[0]);
        const to = boxes.find(b => b.id === e[2]);
        assert.ok(from && to, "all patch cords reference real objects");
        assert.ok(e[1] < from.numoutlets && e[3] < to.numinlets, "valid inlet/outlet indexes");
    }

    const bytes = await readFile(`${outputDir}/ROLI Controls.amxd`);
    assert.equal(bytes.toString("ascii", 0, 4), "ampf");
    assert.equal(bytes.toString("ascii", 8, 12), "aaaa", "Live must recognize a Max Audio Effect");
    assert.equal(bytes.toString("ascii", 24, 28), "ptch");
    assert.equal(bytes.readUInt32LE(28), bytes.length - 32);
    assert.equal(bytes.toString("ascii", 32, 36), "mx@c");
    const jsonEnd = 32 + bytes.readUInt32BE(44) - 2;
    assert.deepEqual(JSON.parse(bytes.toString("utf8", 48, jsonEnd)), patch);
    assert.deepEqual(JSON.parse(await readFile(`${outputDir}/ROLI Controls.maxpat`, "utf8")), patch);
});
