// @device midi-effect
// @ui live.text "Key colors" trigger inlet=1
// @ui live.text "Scale lighting" trigger inlet=2
// @ui live.text "Playing notes" trigger inlet=3
// @ui live.text "Root color" trigger inlet=4
inlets = 5;
outlets = 5;

var surface = null;
var pollTask = null;
var lastError = "";

function status(text) {
    outlet(4, "set", text);
}

function buttonText(index, text) {
    outlet(index, "text", text);
    outlet(index, "texton", text);
}

function disableControls() {
    for (var i = 0; i < 4; i++) {
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
    var reply = api.call("get_roli_controls_state_v3");
    var text = Array.isArray(reply) ? reply.join(" ") : String(reply);
    var match = /^roli_controls_v3 ([01]) ([01]) ([01]) ([01]) ([01]) ([01])$/.exec(text);
    if (!match) {
        throw new Error("Update ROLI script: unexpected reply " + text);
    }
    return {
        white: Number(match[1]), scale: Number(match[2]), notes: Number(match[3]),
        root: Number(match[4]), ready: match[5] === "1", settingsOk: match[6] === "1"
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
                String(candidate.info).indexOf("get_roli_controls_state_v3") !== -1) {
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
        outlet(0, "active", state.scale);
        outlet(1, "active", 1);
        outlet(2, "active", 1);
        outlet(3, "active", state.scale);
        if (!state.settingsOk) {
            reportError("Settings file error.\nSee Live log.");
        } else {
            status(state.ready ? (state.scale ? "Connected" : "Connected\nROLI lighting restored") :
                "Disconnected");
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
    if (inlet >= 1 && inlet <= 4) {
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
    var fields = ["white", "scale", "notes", "root"];
    var methods = ["set_roli_white_keys", "set_roli_scale_lighting", "set_roli_playing_notes",
        "set_roli_root_color"];
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
