"""
PyFluent Protocol Template

The LLM should ONLY generate the function body for `def protocol(protocol):`.
Do not change the function signature. Use the provided `protocol` object to
add labware and perform FCA operations via chainable methods.
"""

TEMPLATE = """
from typing import Any

def protocol(protocol):
    """
    Entry point for pyFluent protocol generation.

    The `protocol` object exposes:
      - add_labware(labware_type, labware_label, location, position)
      - fca().get_tips(tip_type, channels).aspirate(...).dispense(...).drop_tips()
    """

    # [AGENT_FUNCTION_BODY]
    pass
"""





