// @device midi-effect
// @ui live.text "Key colors" trigger inlet=1
// @ui live.text "Scale lighting" trigger inlet=2
// @ui live.text "Playing notes" trigger inlet=3
// @ui live.text "Root color" trigger inlet=4
// @ui live.text "Clip scale" trigger inlet=5
inlets = 6;
outlets = 6;

var surface = null;
var pollTask = null;
var lastError = "";

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
}

function reportError(text) {
    status(text);
    if (text !== lastError) {
        post("ROLI Controls: " + text + "\n");
        lastError = text;
    }
}

function readState(api) {
    var reply = api.call("get_roli_controls_state_v4");
    var text = Array.isArray(reply) ? reply.join(" ") : String(reply);
    var match = /^roli_controls_v4 ([01]) ([01]) ([01]) ([01]) ([01]) ([01]) ([01]) (live|clip|idle|unsupported|error|off)$/.exec(text);
    if (!match) {
        throw new Error("Update ROLI script: unexpected reply " + text);
    }
    return {
        white: Number(match[1]), scale: Number(match[2]), notes: Number(match[3]),
        root: Number(match[4]), clip: Number(match[5]), ready: match[6] === "1",
        settingsOk: match[7] === "1", source: match[8]
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
                String(candidate.info).indexOf("get_roli_controls_state_v4") !== -1) {
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
                    text += "\nROLI lighting restored";
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
    }
    // live.thisdevice starts this after Live's API is available.
    pollTask = new Task(refresh, this);
    pollTask.interval = 500;
    refresh();
    pollTask.repeat();
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

function notifydeleted() {
    if (pollTask) {
        pollTask.cancel();
        pollTask = null;
    }
    surface = null;
}
