import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { compile } from "js2max/dist/compiler/generator.js";
import { buildAmxd } from "js2max/dist/amxd/writer.js";

const source = fileURLToPath(new URL("./ROLI-Controls.js", import.meta.url));
export const outputDir = fileURLToPath(new URL("../dist/m4l/", import.meta.url));

export async function build() {
    const patch = await compile(source, { deviceWidth: 376 });
    const p = patch.patcher;
    const boxes = p.boxes.map(({ box }) => box);
    const script = boxes.find(box => box.text === "v8");
    const audioIn = boxes.find(box => box.text === "plugin~");
    const audioOut = boxes.find(box => box.text === "plugout~");
    const controls = boxes.filter(box => box.maxclass === "live.text");
    const sliders = boxes.filter(box => box.maxclass === "live.slider");
    if (!script || !audioIn || !audioOut || controls.length !== 7 || sliders.length !== 2) {
        throw new Error("Unexpected js2max template; cannot safely wire controls");
    }
    p.boxes = p.boxes.filter(({ box }) => box.maxclass !== "comment");

    // Keep stereo audio at unity gain, outside JavaScript and the control bridge.
    p.lines = p.lines.filter(({ patchline }) =>
        patchline.source[0] !== audioIn.id && patchline.destination[0] !== audioOut.id);
    for (let channel = 0; channel < 2; channel++) {
        p.lines.push({ patchline: { source: [audioIn.id, channel], destination: [audioOut.id, channel] } });
    }
    const names = ["key_colors", "scale_lighting", "playing_notes", "root_color", "clip_scale",
        "pitch_bend", "pressure"];
    const presentationOrder = ["scale_lighting", "clip_scale", "key_colors", "root_color", "playing_notes"];
    const annotations = [
        "Cycles White, Track, Rainbow. Rainbow follows Live's scale with the native rainbow palette; Root color and Background Brightness are saved but inactive. Used when Scale lighting is on.",
        "Off restores the keyboard's captured pre-script lighting settings. Navigation and MPE remain active.",
        "Controls Live's note feedback and playing-clip highlighting, not the Piano's native touch/pressure lighting.",
        "Off makes root keys match the other lit keys, without changing notes or scale membership. Used when Scale lighting is on with White or Track colors; saved but inactive in Rainbow.",
        "On follows the selected track's playing MIDI clip root, scale and Scale mode independently of Live's global Scale mode switch. Falls back to Live's global scale settings when no applicable clip plays or clip-scale API is unavailable. Off always follows Live's global scale settings. Requires Live 12.4.15b1 or newer. Used when Scale lighting is on, including Rainbow.",
        "Enables or disables native pitch bend on a connected Piano 49. Independent of lighting and pressure; MPE remains enabled. Saved across restarts. Previous native settings are restored on script shutdown. Unavailable on unverified Piano M/LUMI profiles.",
        "Enables or disables native pressure (aftertouch) on a connected Piano 49, not note velocity. Independent of lighting and pitch bend; MPE remains enabled. Saved across restarts. Previous native settings are restored on script shutdown. Unavailable on unverified Piano M/LUMI profiles."
    ];
    controls.forEach((control, index) => {
        const outlet = index < 5 ? index : index + 4;
        p.lines.push({ patchline: { source: [script.id, outlet], destination: [control.id, 0] } });
        control.mode = 0;
        control.numoutlets = 2;
        control.outlettype = ["", ""];
        control.varname = names[index];
        control.parameter_enable = 0;
        control.active = 0;
        control.annotation = annotations[index];
        control.presentation_rect = index < 5 ?
            [8, 6 + presentationOrder.indexOf(control.varname) * 25, 124, 24] :
            [244, 36 + (index - 5) * 25, 124, 24];
        control.fontsize = 10;
        control.fontface = 0;
        control.rounded = 2;
        control.saved_object_attributes = { parameter_enable: 0 };
        control.saved_attribute_attributes = {
            activebgcolor: { expression: "themecolor.live_control_bg" },
            activebgoncolor: { expression: "themecolor.live_control_selection" },
            activetextcolor: { expression: "themecolor.live_control_fg_off" },
            activetextoncolor: { expression: "themecolor.live_control_fg_on" },
            bordercolor: { expression: "themecolor.live_contrast_frame" },
            focusbordercolor: { expression: "themecolor.live_focus_frame" }
        };
    });

    p.boxes.push({ box: {
        id: "label-expression", maxclass: "comment", numinlets: 1, numoutlets: 0,
        text: "Expression", patching_rect: [244, 570, 124, 24],
        presentation: 1, presentation_rect: [244, 6, 124, 24],
        fontsize: 10,
        saved_attribute_attributes: { textcolor: { expression: "themecolor.live_control_fg" } }
    } });

    const levels = [
        ["global_brightness", "Global\nBrightness (%)", 100,
            "Global LED brightness, including playback highlights. Double-click resets to 100%. Works with Scale lighting on or off. Saved only when changed; script shutdown restores the captured hardware brightness."],
        ["background_intensity", "Background\nBrightness (%)", 25,
            "Background and root RGB intensity relative to playback highlights. Double-click resets to 25%. Used when Scale lighting is on with White or Track colors; saved but inactive in Rainbow. This is an RGB percentage, not calibrated perceptual brightness."]
    ];
    sliders.forEach((slider, index) => {
        const [name, label, resetValue, annotation] = levels[index];
        const y = 6 + index * 64;
        slider.varname = name;
        slider.parameter_enable = 1;
        slider.active = 0;
        slider.orientation = 1;
        slider.showname = 0;
        slider.shownumber = 1;
        slider.fontsize = 10;
        slider.annotation = annotation;
        slider.presentation_rect = [144, y + 30, 88, 28];
        slider.saved_object_attributes = { parameter_enable: 1 };
        slider.saved_attribute_attributes = {
            valueof: {
                parameter_longname: name, parameter_shortname: label.replace("\n", " "),
                parameter_type: 1, parameter_mmin: 0, parameter_mmax: 100,
                parameter_initial: [resetValue],
                parameter_initial_enable: 0, parameter_invisible: 2
            },
            slidercolor: { expression: "themecolor.live_control_fg" },
            textcolor: { expression: "themecolor.live_control_fg" },
            focusbordercolor: { expression: "themecolor.live_focus_frame" }
        };
        p.lines.push({ patchline: { source: [script.id, index + 6], destination: [slider.id, 0] } });
        p.boxes.push({ box: {
            id: `label-${name}`, maxclass: "comment", numinlets: 1, numoutlets: 0,
            text: label, annotation,
            patching_rect: [144, 570 + index * 32, 88, 28],
            presentation: 1, presentation_rect: [144, y, 88, 28],
            fontsize: 10, linecount: 2,
            saved_attribute_attributes: { textcolor: { expression: "themecolor.live_control_fg" } }
        } });
    });

    const statusId = "roli-status";
    const connectionId = "roli-connection";
    p.boxes.push({ box: {
        id: connectionId, maxclass: "led", numinlets: 1, numoutlets: 1, outlettype: ["int"],
        patching_rect: [144, 530, 6, 6],
        presentation: 1, presentation_rect: [8, 147, 6, 6],
        ignoreclick: 1, parameter_enable: 0,
        annotation: "Waiting for Live API...",
        saved_attribute_attributes: {
            bgcolor: { expression: "themecolor.live_surface_bg" },
            oncolor: { expression: "themecolor.live_control_selection" },
            offcolor: { expression: "themecolor.live_control_fg_off" }
        }
    } });
    p.boxes.push({ box: {
        id: statusId, maxclass: "comment", numinlets: 1, numoutlets: 0,
        text: "Waiting for Live API...",
        patching_rect: [10, 530, 350, 16],
        presentation: 1, presentation_rect: [18, 143, 350, 16],
        fontsize: 10, linecount: 1,
        saved_attribute_attributes: {
            textcolor: { expression: "themecolor.live_control_fg" }
        }
    } });
    p.lines.push({ patchline: { source: [script.id, 5], destination: [statusId, 0] } });
    p.lines.push({ patchline: { source: [script.id, 8], destination: [connectionId, 0] } });
    const dividers = [
        ["columns", [138, 6, 1, 124]],
        ["brightness", [144, 67, 88, 1]],
        ["status", [8, 132, 360, 1]],
        ["expression", [238, 6, 1, 124]]
    ];
    dividers.forEach(([name, rect], index) => {
        p.boxes.push({ box: {
            id: `divider-${name}`, maxclass: "live.line", numinlets: 1, numoutlets: 0,
            patching_rect: [144, 650 + index * 20, rect[2], rect[3]],
            presentation: 1, presentation_rect: rect,
            orientation: rect[2] > rect[3] ? 1 : 0,
            justification: 1, border: 1, ignoreclick: 1,
            saved_attribute_attributes: {
                linecolor: { expression: "themecolor.live_contrast_frame" }
            }
        } });
    });
    p.default_fontsize = 10;
    p.saved_attribute_attributes = {
        bgcolor: { expression: "themecolor.live_surface_bg" },
        editing_bgcolor: { expression: "themecolor.live_surface_bg" }
    };
    await mkdir(outputDir, { recursive: true });
    await writeFile(`${outputDir}/ROLI Controls.maxpat`, JSON.stringify(patch, null, 2));
    await writeFile(`${outputDir}/ROLI Controls.amxd`, buildAmxd(patch, "audio-effect", "ROLI Controls.amxd"));
    return patch;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
    await build();
    console.log(`Built ${outputDir}/ROLI Controls.amxd`);
}
