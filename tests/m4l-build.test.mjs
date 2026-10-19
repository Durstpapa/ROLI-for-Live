import test from "node:test";
import assert from "node:assert/strict";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import { build, outputDir } from "../m4l/build.mjs";

test("generated audio effect embeds JS, passes stereo audio directly, and wires confirmed UI state", async () => {
    const legacyNames = ["ROLI Controls.amxd", "ROLI Controls.maxpat"];
    await mkdir(outputDir, { recursive: true });
    for (const name of legacyNames) {
        await writeFile(`${outputDir}/${name}`, "legacy generated device");
    }
    const patch = await build();
    for (const name of legacyNames) {
        await assert.rejects(access(`${outputDir}/${name}`), { code: "ENOENT" },
            "renamed builds must remove stale generated files under the former device name");
    }
    const p = patch.patcher;
    const boxes = p.boxes.map(({ box }) => box);
    const script = boxes.find(b => b.text === "v8");
    const audioIn = boxes.find(b => b.text === "plugin~");
    const audioOut = boxes.find(b => b.text === "plugout~");
    const toggle = boxes.find(b => b.varname === "key_colors");
    const init = boxes.find(b => b.text === "live.thisdevice");
    const edges = p.lines.map(({ patchline: l }) => [...l.source, ...l.destination]);
    const hasEdge = (from, outlet, to, inlet) =>
        edges.some(e => JSON.stringify(e) === JSON.stringify([from, outlet, to, inlet]));
    assert.equal(script.textfile.embed, 1);
    assert.match(script.textfile.text, /function readState/);
    assert.equal(p.openinpresentation, 1);
    assert.equal(p.devicewidth, 376, "expression column extends the existing lighting and brightness layout");
    assert.equal(p.saved_attribute_attributes.bgcolor.expression, "themecolor.live_surface_bg");
    assert.equal(toggle.saved_attribute_attributes.activebgcolor.expression, "themecolor.live_control_bg");
    assert.equal(toggle.saved_attribute_attributes.focusbordercolor.expression, "themecolor.live_focus_frame");
    const visible = boxes.filter(b => b.presentation === 1);
    assert.equal(visible.length, 18, "seven buttons, expression heading, status and dot, two sliders and labels, four dividers");
    assert.deepEqual(
        visible.filter(b => b.maxclass === "live.text" && b.presentation_rect[0] === 8)
            .sort((a, b) => a.presentation_rect[1] - b.presentation_rect[1])
            .map(b => b.varname),
        ["scale_lighting", "clip_scale", "key_colors", "root_color", "playing_notes"],
        "requested top-to-bottom order must not change inlet/outlet semantics");
    assert.ok(!visible.some(b => /proof of concept|js2max|Live color switch/i.test(b.text)));
    for (const box of visible) {
        const [x, y, width, height] = box.presentation_rect;
        assert.ok(x >= 0 && y >= 0 && x + width <= 376 && y + height <= 169,
            "all presentation content fits the compact device strip");
        if (box.maxclass !== "live.line" && box.maxclass !== "led") {
            assert.equal(box.fontsize, 10, "all controls, labels and status use consistent text sizes");
        }
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
    const dividers = visible.filter(b => b.maxclass === "live.line");
    assert.deepEqual(dividers.map(b => [b.id, b.presentation_rect, b.orientation]), [
        ["divider-columns", [138, 6, 1, 124], 0],
        ["divider-brightness", [144, 67, 88, 1], 1],
        ["divider-status", [8, 132, 360, 1], 1],
        ["divider-expression", [238, 6, 1, 124], 0]
    ], "column dividers stop above the full-width status strip");
    for (const divider of dividers) {
        assert.equal(divider.border, 1);
        assert.equal(divider.justification, 1);
        assert.equal(divider.ignoreclick, 1, "decorative dividers must not capture clicks");
        assert.equal(divider.saved_attribute_attributes.linecolor.expression, "themecolor.live_contrast_frame");
        assert.ok(!edges.some(e => e[0] === divider.id || e[2] === divider.id),
            "dividers must not change control or audio routing");
    }
    assert.equal(toggle.active, 0, "must wait for script confirmation");
    assert.equal(toggle.mode, 0, "momentary clicks must invert script state, not widget state");
    assert.equal(toggle.parameter_enable, 0, "POC must not restore a stale saved preference");
    assert.match(toggle.annotation, /White, Track, Rainbow/);
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
    assert.equal(script.numinlets, 10);
    assert.equal(script.numoutlets, 11);
    for (const [index, name] of ["key_colors", "scale_lighting", "playing_notes", "root_color", "clip_scale"].entries()) {
        const control = boxes.find(b => b.varname === name);
        assert.ok(hasEdge(control.id, 0, script.id, index + 1));
        assert.ok(hasEdge(script.id, index, control.id, 0));
        assert.equal(control.mode, 0);
        assert.equal(control.active, 0);
        assert.equal(control.parameter_enable, 0);
        assert.ok(control.presentation_rect[2] >= 24 && control.presentation_rect[3] >= 24);
    }
    assert.ok(hasEdge(script.id, 5, "roli-status", 0));
    assert.equal(boxes.find(b => b.id === "label-expression").text, "Expression");
    for (const [name, inlet, outlet, y] of [["pitch_bend", 8, 9, 36], ["pressure", 9, 10, 61]]) {
        const control = boxes.find(b => b.varname === name);
        assert.deepEqual(control.presentation_rect, [244, y, 124, 24]);
        assert.ok(hasEdge(control.id, 0, script.id, inlet));
        assert.ok(hasEdge(script.id, outlet, control.id, 0));
        assert.equal(control.mode, 0);
        assert.equal(control.parameter_enable, 0);
        assert.equal(control.active, 0);
        assert.match(control.annotation, /Piano M\/LUMI support is experimental/);
    }
    assert.match(boxes.find(b => b.varname === "pressure").annotation, /not note velocity/);
    assert.ok(hasEdge(script.id, 8, "roli-connection", 0));
    const connection = boxes.find(b => b.id === "roli-connection");
    const status = boxes.find(b => b.id === "roli-status");
    assert.equal(connection.maxclass, "led");
    assert.equal(connection.ignoreclick, 1, "connection dot is not a control");
    assert.equal(connection.parameter_enable, 0, "connection state must not be restored as a preference");
    assert.equal(connection.saved_attribute_attributes.oncolor.expression, "themecolor.live_control_selection");
    assert.equal(connection.saved_attribute_attributes.offcolor.expression, "themecolor.live_control_fg_off");
    assert.equal(connection.saved_attribute_attributes.bgcolor.expression, "themecolor.live_surface_bg");
    assert.deepEqual(connection.presentation_rect, [8, 147, 6, 6]);
    assert.deepEqual(status.presentation_rect, [18, 143, 350, 16]);
    const divider = boxes.find(b => b.id === "divider-status");
    const footerTop = divider.presentation_rect[1] + divider.presentation_rect[3];
    const footerCenter = (footerTop + 169) / 2;
    assert.equal(status.presentation_rect[1] + status.presentation_rect[3] / 2, footerCenter,
        "status text is vertically centered in the available footer space");
    assert.equal(connection.presentation_rect[1] + connection.presentation_rect[3] / 2, footerCenter - 1,
        "dot is optically aligned one unit above the text-box center to match the visible letters");
    assert.ok(!boxes.some(b => b.id === "roli-connection-label"), "one text object owns connection and scale alignment");
    assert.ok(status.presentation_rect[2] >= 3 * 114, "status text gets at least three times its previous width");
    assert.equal(status.presentation_rect[0] + status.presentation_rect[2], p.devicewidth - 8);
    assert.equal(status.linecount, 1, "connection, source and Scale mode share one centered row at 10 points");
    for (const control of visible.filter(b => b.maxclass === "live.text" || b.maxclass === "live.slider")) {
        assert.ok(control.presentation_rect[1] + control.presentation_rect[3] <= 130,
            "all interactive controls stay above the status divider");
    }
    assert.ok(!edges.some(e => e[0] === connection.id), "indicator must never send control commands");
    const clipControl = boxes.find(b => b.varname === "clip_scale");
    assert.equal(clipControl.text, "Follow clip scale");
    assert.match(clipControl.annotation, /independently of Live's global Scale mode switch/);
    assert.match(clipControl.annotation, /Falls back to Live's global scale settings/);
    assert.equal(clipControl.presentation_rect[1], 31, "source override sits immediately below Scale lighting");
    const notesControl = boxes.find(b => b.varname === "playing_notes");
    assert.equal(notesControl.text, "Show playing notes");
    assert.equal(notesControl.presentation_rect[1], 106, "note feedback is the last control");
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

    const bytes = await readFile(`${outputDir}/ROLI Piano Controls.amxd`);
    assert.equal(bytes.toString("ascii", 0, 4), "ampf");
    assert.equal(bytes.toString("ascii", 8, 12), "aaaa", "Live must recognize a Max Audio Effect");
    assert.equal(bytes.toString("ascii", 24, 28), "ptch");
    assert.equal(bytes.readUInt32LE(28), bytes.length - 32);
    assert.equal(bytes.toString("ascii", 32, 36), "mx@c");
    const jsonEnd = 32 + bytes.readUInt32BE(44) - 2;
    assert.deepEqual(JSON.parse(bytes.toString("utf8", 48, jsonEnd)), patch);
    assert.deepEqual(JSON.parse(await readFile(`${outputDir}/ROLI Piano Controls.maxpat`, "utf8")), patch);
});
