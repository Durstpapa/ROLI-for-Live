from __future__ import absolute_import, print_function, unicode_literals

from _Framework.Capabilities import (AUTO_LOAD_KEY, CONTROLLER_ID_KEY, NOTES_CC, PORTS_KEY, SCRIPT,
                                     controller_id, inport, outport)

from .roli_for_live import ROLIForLive

__version__ = '0.1.0'


def get_capabilities():
    return {
        CONTROLLER_ID_KEY: controller_id(vendor_id=0x2AF4, product_ids=[0x0F00], model_name='ROLI Piano'),
        PORTS_KEY: [inport(props=[NOTES_CC, SCRIPT]), outport(props=[SCRIPT])],
        AUTO_LOAD_KEY: True,
    }


def create_instance(c_instance):
    return ROLIForLive(c_instance)
