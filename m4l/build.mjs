import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { compile } from "js2max/dist/compiler/generator.js";
import { buildAmxd } from "js2max/dist/amxd/writer.js";

const source = fileURLToPath(new URL("./ROLI-Controls.js", import.meta.url));
export const outputDir = fileURLToPath(new URL("../dist/m4l/", import.meta.url));

export async function build() {
    const patch = await compile(source, { deviceWidth: 240 });
    const p = patch.patcher;
    const boxes = p.boxes.map(({ box }) => box);
    const script = boxes.find(box => box.text === "v8");
    const midiIn = boxes.find(box => box.text === "midiin");
    const midiOut = boxes.find(box => box.text === "midiout");
    const controls = boxes.filter(box => box.maxclass === "live.text");
    const sliders = boxes.filter(box => box.maxclass === "live.slider");
    if (!script || !midiIn || !midiOut || controls.length !== 5 || sliders.length !== 2) {
        throw new Error("Unexpected js2max template; cannot safely wire controls");
    }
    p.boxes = p.boxes.filter(({ box }) => box.maxclass !== "comment");

    // Keep all performance MIDI out of JavaScript, including MPE and SysEx.
    p.lines = p.lines.filter(({ patchline }) =>
        patchline.source[0] !== midiIn.id && patchline.destination[0] !== midiOut.id);
    p.lines.push({ patchline: { source: [midiIn.id, 0], destination: [midiOut.id, 0] } });
    const names = ["white_keys", "scale_lighting", "playing_notes", "root_color", "clip_scale"];
    const presentationOrder = ["scale_lighting", "white_keys", "root_color", "playing_notes", "clip_scale"];
    const annotations = [
        "White keys with track-colored roots, or track-colored keys with brighter roots. Used when Scale lighting is on.",
        "Off restores the keyboard's captured pre-script lighting settings. Navigation and MPE remain active.",
        "Controls Live's note feedback and playing-clip highlighting, not the Piano's native touch/pressure lighting.",
        "Off makes root keys match the other lit keys, without changing notes or scale membership. Used when Scale lighting is on.",
        "On follows the selected track's playing MIDI clip scale without selecting it. Off follows Live's global scale. Falls back to Live when no clip plays or clip-scale API is unavailable. Requires Live 12.4.15b1 or newer. Used when Scale lighting is on."
    ];
    controls.forEach((control, index) => {
        p.lines.push({ patchline: { source: [script.id, index], destination: [control.id, 0] } });
        control.mode = 0;
        control.numoutlets = 2;
        control.outlettype = ["", ""];
        control.varname = names[index];
        control.parameter_enable = 0;
        control.active = 0;
        control.annotation = annotations[index];
        control.presentation_rect = [8, 6 + presentationOrder.indexOf(control.varname) * 25, 124, 24];
        control.fontsize = 11;
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

    const levels = [
        ["global_brightness", "Global\nBrightness (%)",
            "Global LED brightness, including playback highlights. Works with Scale lighting on or off. Saved only when changed; script shutdown restores the captured hardware brightness."],
        ["background_intensity", "Background\nBrightness (%)",
            "Background and root RGB intensity relative to playback highlights. Used when Scale lighting is on. This is an RGB percentage, not calibrated perceptual brightness."]
    ];
    sliders.forEach((slider, index) => {
        const [name, label, annotation] = levels[index];
        const y = 6 + index * 76;
        slider.varname = name;
        slider.parameter_enable = 1;
        slider.active = 0;
        slider.orientation = 1;
        slider.showname = 0;
        slider.shownumber = 1;
        slider.fontsize = 11;
        slider.annotation = annotation;
        slider.presentation_rect = [144, y + 30, 88, 28];
        slider.saved_object_attributes = { parameter_enable: 1 };
        slider.saved_attribute_attributes = {
            valueof: {
                parameter_longname: name, parameter_shortname: label.replace("\n", " "),
                parameter_type: 1, parameter_mmin: 0, parameter_mmax: 100,
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

    // A text acknowledgement is deliberately not a green hardware-confirmation LED.
    const statusId = "roli-status";
    p.boxes.push({ box: {
        id: statusId, maxclass: "comment", numinlets: 1, numoutlets: 0,
        text: "Waiting for Live API...",
        patching_rect: [10, 530, 124, 36],
        presentation: 1, presentation_rect: [8, 133, 124, 36],
        fontsize: 10, linecount: 3,
        saved_attribute_attributes: {
            textcolor: { expression: "themecolor.live_control_fg" }
        }
    } });
    p.lines.push({ patchline: { source: [script.id, 5], destination: [statusId, 0] } });
    p.default_fontsize = 11;
    p.saved_attribute_attributes = {
        bgcolor: { expression: "themecolor.live_surface_bg" },
        editing_bgcolor: { expression: "themecolor.live_surface_bg" }
    };
    await mkdir(outputDir, { recursive: true });
    await writeFile(`${outputDir}/ROLI Controls.maxpat`, JSON.stringify(patch, null, 2));
    await writeFile(`${outputDir}/ROLI Controls.amxd`, buildAmxd(patch, "midi-effect", "ROLI Controls.amxd"));
    return patch;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
    await build();
    console.log(`Built ${outputDir}/ROLI Controls.amxd`);
}
