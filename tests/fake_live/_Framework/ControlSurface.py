import contextlib


class Observable(object):
    """Mimics Live's listener rules: adding the same callable twice raises."""
    def __init__(self, **props):
        self._props = dict(props)
        self._listeners = {}
        for name in props:
            setattr(self, 'add_%s_listener' % name, self._adder(name))
            setattr(self, 'remove_%s_listener' % name, self._remover(name))
            setattr(self, '%s_has_listener' % name, self._has(name))

    def __getattr__(self, name):
        props = self.__dict__.get('_props', {})
        if name in props:
            return props[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name.startswith('_') or name not in self.__dict__.get('_props', {}):
            object.__setattr__(self, name, value)
            return
        self._props[name] = value
        for cb in list(self._listeners.get(name, [])):
            cb()

    def _adder(self, name):
        def add(cb):
            lst = self._listeners.setdefault(name, [])
            if cb in lst:
                raise RuntimeError('Observer already connected')
            lst.append(cb)
        return add

    def _remover(self, name):
        return lambda cb: self._listeners[name].remove(cb)

    def _has(self, name):
        return lambda cb: cb in self._listeners.get(name, [])


class ControlSurface(object):
    song_instance = None
    sent = []
    notes_out = []
    logs = []

    def __init__(self, c_instance):
        self._c_instance = c_instance
        self.song().view.add_selected_track_listener(self._on_selected_track_changed)
        self._c_instance = c_instance

    def _on_selected_track_changed(self):
        pass

    def song(self):
        return ControlSurface.song_instance

    @contextlib.contextmanager
    def component_guard(self):
        yield

    def _send_midi(self, midi_bytes, optimized=True):
        assert all(isinstance(b, int) and 0 <= b < 256 for b in midi_bytes)
        if midi_bytes[0] == 0xF0:
            assert midi_bytes[-1] == 0xF7
            ControlSurface.sent.append(tuple(midi_bytes))
        else:
            assert len(midi_bytes) == 3
            ControlSurface.notes_out.append(tuple(midi_bytes))
        return True

    def log_message(self, *a):
        ControlSurface.logs.append(' '.join(str(x) for x in a))

    def show_message(self, msg):
        ControlSurface.logs.append('SHOW: ' + msg)

    controlled_track = None
    feedback_channels = None

    def set_controlled_track(self, track):
        ControlSurface.controlled_track = track

    def release_controlled_track(self):
        ControlSurface.controlled_track = None

    def set_feedback_channels(self, channels):
        ControlSurface.feedback_channels = list(channels)

    def update_display(self): pass
    def disconnect(self): pass
    def port_settings_changed(self): pass
    def refresh_state(self): pass
