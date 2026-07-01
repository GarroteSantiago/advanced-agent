# Notes

- A harness acts DURING the task and is composed by:
  - An agent loop, that interleaves reasoning, action and observation
    - Use inputControll for this
  - A tool interface, that lets models perceive and alter the environment
  - Context management, that decides what enters and leaves the model's window
  - Control mechanisms, (limits, verification and deterministic actions)
    - Makes the execution more trustworthy, auditable, and contained
