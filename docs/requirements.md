# Kickoff meeting notes

## Requirements

- The simulator MUST be able to scale up to 128 RTs per AP
- The simulator MUST be able to scale up to 15000 APs
- AP/RT combinations SHOULD be able to be created in batches with a single request
- AP/RT actions MAY be staggered over time
- A simulator environment SHOULD be configurable from a single config file
- The simulator MUST offer a REST API for managing APs and RTs
- It SHOULD be possible to configure the simulator in real-time from a web interface
- The simulator SHOULD be able to run in one or more containers
- The simulator MUST provide self-referential performance metrics
- The simulator MUST provide bulk performance metrics for the APs and RTs
- Actions SHOULD be programmable with failure rates.

AP nodesim requirements

- An AP node MUST support the following actions (in effect the mirror image of the SB API):
  - Registration
    - Including certificate exchange once implemented on NMS
  - Send Heartbeat
  - Send alarms
    - platform
    - O1 alarms
    - RC alarms
  - Send performance data
    - O1
    - Platform
  - pull s/w upgrade
  - Send log files
  - Send audit logs
  - Reboot
  - Pull configuration
  - Start of day procedure

RT requirements

- RT nodesim MUST support actions as supplied by the design spec (Joe to supply)

Initial implementatin order

1. AP registration
2. AP heartbeat
3. RT registration
4. RT heartbeat
