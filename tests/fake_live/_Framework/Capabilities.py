AUTO_LOAD_KEY, CONTROLLER_ID_KEY, PORTS_KEY = 'auto_load', 'controller_id', 'ports'
NOTES_CC, SCRIPT = 'notes_cc', 'script'
def controller_id(**kw): return kw
def inport(props=()): return {'direction': 'in', 'props': props}
def outport(props=()): return {'direction': 'out', 'props': props}
