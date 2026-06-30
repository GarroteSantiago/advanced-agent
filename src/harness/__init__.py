"""The harness: everything that acts during a task.

Interleaves reasoning, action, and observation (``loop``); lets the agent
perceive and alter its environment (``tools``); decides what enters the model's
window (``context``, a deferred seam); and keeps the run contained and auditable
(``control``, ``events``). ``Harness`` is the composition root that wires it all.
"""

from harness.harness import Harness

__all__ = ["Harness"]
