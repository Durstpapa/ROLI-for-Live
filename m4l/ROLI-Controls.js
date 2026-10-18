// @device audio-effect
// @ui live.text "Key colors" trigger inlet=1
// @ui live.text "Scale lighting" trigger inlet=2
// @ui live.text "Playing notes" trigger inlet=3
// @ui live.text "Root color" trigger inlet=4
// @ui live.text "Clip scale" trigger inlet=5
// @ui live.slider "Global brightness" inlet=6 min=0 max=100
// @ui live.slider "Background intensity" inlet=7 min=0 max=100
inlets = 8;
outlets = 8;

var surface = null;
var pollTask = null;
var lastError = "";
var levelTask = null;
var pendingLevels = {};

function status(text) {
    outlet(5, "set", text);
    outlet(5, "annotation", text);
}

function buttonText(index, text) {
    outlet(index, "text", text);
    outlet(index, "texton", text);
}

function disableControls() {
    for (var i = 0; i < 5; i++) {
        outlet(i, "active", 0);
    }
    outlet(6, "active", 0);
    outlet(7, "active", 0);
}

function reportError(text) {
    status(text);
    if (text !== lastError) {
        post("ROLI Controls: " + text + "\n");
        lastError = text;
    }
}

function readState(api) {
    var reply = api.call("get_roli_controls_state_v5");
    var text = Array.isArray(reply) ? reply.join(" ") : String(reply);
    var match = /^roli_controls_v5 ([01]) ([01]) ([01]) ([01]) ([01]) ([01]) ([01]) (live|clip|idle|unsupported|error|off) (-1|\d{1,3}) (\d{1,3})$/.exec(text);
    if (!match || Number(match[9]) > 100 || Number(match[10]) > 100) {
        throw new Error("Update ROLI script: unexpected reply " + text);
    }
    return {
        white: Number(match[1]), scale: Number(match[2]), notes: Number(match[3]),
        root: Number(match[4]), clip: Number(match[5]), ready: match[6] === "1",
        settingsOk: match[7] === "1", source: match[8],
        brightness: Number(match[9]), background: Number(match[10])
    };
}

function findSurface() {
    var app = new LiveAPI(null, "live_app");
    var ids = app.get("control_surfaces");
    var matches = [];
    for (var i = 0; i < ids.length; i++) {
        if (ids[i] !== "id" || !Number(ids[i + 1])) {
            continue;
        }
        var candidate = new LiveAPI(null, "id " + ids[++i]);
        if (candidate.type === "ROLIForLive" ||
                String(candidate.info).indexOf("get_roli_controls_state_v5") !== -1) {
            matches.push(candidate);
        }
    }
    if (matches.length !== 1) {
        throw new Error(matches.length ? "Enable only one ROLI for Live surface" :
            "Disconnected");
    }
    return matches[0];
}

function refresh() {
    try {
        surface = findSurface();
        var state = readState(surface);
        buttonText(0, state.white ? "Key colors: White" : "Key colors: Track");
        buttonText(1, state.scale ? "Scale lighting: ON" : "Scale lighting: OFF");
        buttonText(2, state.notes ? "Playing notes: ON" : "Playing notes: OFF");
        buttonText(3, state.root ? "Root color: ON" : "Root color: OFF");
        buttonText(4, state.clip ? "Clip scale: ON" : "Clip scale: OFF");
        outlet(0, "active", state.scale);
        outlet(1, "active", 1);
        outlet(2, "active", 1);
        outlet(3, "active", state.scale);
        outlet(4, "active", state.scale);
        if (state.brightness >= 0 && pendingLevels[0] === undefined) {
            outlet(6, "set", state.brightness);
        }
        if (pendingLevels[1] === undefined) {
            outlet(7, "set", state.background);
        }
        outlet(6, "active", state.ready && state.brightness >= 0 ? 1 : 0);
        outlet(7, "active", state.ready && state.scale ? 1 : 0);
        if (!state.settingsOk) {
            reportError("Settings file error.\nSee Live log.");
        } else if (state.ready && state.scale && state.source === "unsupported") {
            reportError("Connected\nClip scale unavailable\nUsing Live scale");
        } else if (state.ready && state.scale && state.source === "error") {
            reportError("Connected\nClip scale read error\nUsing Live scale");
        } else {
            var text = "Disconnected";
            if (state.ready) {
                text = "Connected";
                if (!state.scale) {
                    text += "\nNative colors restored";
                } else if (state.clip) {
                    text += state.source === "clip" ? "\nPlaying clip scale" : "\nLive scale (no clip)";
                }
            }
            status(text);
            lastError = "";
        }
    } catch (error) {
        surface = null;
        disableControls();
        reportError(String(error.message || error));
        return;
    }
}

function bang() {
    if (inlet >= 1 && inlet <= 5) {
        toggleSetting(inlet - 1);
        return;
    }
    if (pollTask) {
        pollTask.cancel();
        pollTask = null;
    }
    if (levelTask) {
        levelTask.cancel();
        levelTask = null;
    }
    pendingLevels = {};
    try {
        verifySliderRanges();
    } catch (error) {
        disableControls();
        reportError(String(error.message || error));
        return;
    }
    // live.thisdevice starts this after Live's API is available.
    pollTask = new Task(refresh, this);
    pollTask.interval = 500;
    refresh();
    pollTask.repeat();
}

function verifySliderRanges() {
    var names = ["global_brightness", "background_intensity"];
    for (var i = 0; i < names.length; i++) {
        var control = this.patcher.getnamed(names[i]);
        if (!control) {
            throw new Error("Missing brightness slider");
        }
        var previous = Number(control.getvalueof());
        if (!isFinite(previous)) {
            throw new Error("Cannot read brightness slider");
        }
        var minimum, maximum;
        try {
            control.message("set", 100);
            maximum = Number(control.getvalueof());
            control.message("set", 0);
            minimum = Number(control.getvalueof());
        } finally {
            control.message("set", previous);
        }
        if (minimum !== 0 || maximum !== 100) {
            throw new Error("Slider range error.\nReload updated device.");
        }
    }
}

function toggleSetting(index) {
    var fields = ["white", "scale", "notes", "root", "clip"];
    var methods = ["set_roli_white_keys", "set_roli_scale_lighting", "set_roli_playing_notes",
        "set_roli_root_color", "set_roli_clip_scale"];
    try {
        // Rediscover before writes: a removed/reordered surface must never receive a stale command.
        surface = findSurface();
        var field = fields[index];
        var value = 1 - readState(surface)[field];
        surface.call(methods[index], value);
        var confirmed = readState(surface);
        if (!confirmed.settingsOk) {
            throw new Error("Settings were not saved.\nSee Live log.");
        }
        if (confirmed[field] !== value) {
            throw new Error("Script did not accept the requested setting");
        }
    } catch (error) {
        surface = null;
        disableControls();
        reportError(String(error.message || error));
        return;
    }
    refresh();
}

function msg_int(value) {
    queueLevel(value);
}

function msg_float(value) {
    queueLevel(value);
}

function queueLevel(value) {
    if (!pollTask) {
        reportError("Waiting for Live API...");
        return;
    }
    if ((inlet !== 6 && inlet !== 7) || typeof value !== "number" ||
            !isFinite(value) || value < 0 || value > 100) {
        reportError("Invalid brightness input");
        return;
    }
    pendingLevels[inlet - 6] = Math.round(value);
    if (!levelTask) {
        levelTask = new Task(flushLevels, this);
        levelTask.schedule(100);
    }
}

function flushLevels() {
    var levels = pendingLevels;
    pendingLevels = {};
    levelTask = null;
    for (var index = 0; index < 2; index++) {
        if (levels[index] === undefined) {
            continue;
        }
        try {
            surface = findSurface();
            var state = readState(surface);
            if (!state.ready) {
                throw new Error("Disconnected");
            }
            var field = index === 0 ? "brightness" : "background";
            var method = index === 0 ? "set_roli_global_brightness" : "set_roli_background_intensity";
            var value = levels[index];
            if (state[field] !== value || !state.settingsOk) {
                surface.call(method, value);
                var confirmed = readState(surface);
                if (!confirmed.settingsOk) {
                    throw new Error("Settings were not saved.\nSee Live log.");
                }
                if (confirmed[field] !== value) {
                    throw new Error("Script did not accept the requested level");
                }
            }
        } catch (error) {
            surface = null;
            disableControls();
            reportError(String(error.message || error));
            return;
        }
    }
    refresh();
}

function notifydeleted() {
    if (pollTask) {
        pollTask.cancel();
        pollTask = null;
    }
    if (levelTask) {
        levelTask.cancel();
        levelTask = null;
    }
    pendingLevels = {};
    surface = null;
}
