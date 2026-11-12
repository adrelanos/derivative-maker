# config/

Build settings for DhampirOS. These sit on top of upstream defaults. Upstream files are not edited.

Status: **no settings yet.**

Notes for later:

- Config files are loaded after the command line is read (`variables.d/05_load-config.bsh`). Settings that a script reads from its own command-line flags must be passed on the command line, not set here. For example, the ISO name uses `--dist-pretty` (`help-steps/dm-raw-to-iso`).
- Config files must end in `.conf` and are read from `buildconfig.d/`, `/etc/buildconfig-dist.d`, or `--conffile`.
- Each setting will be added only after it is verified.
