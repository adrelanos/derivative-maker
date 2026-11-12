# kernel/

Reserved for future DhampirOS kernel work.

Status: **empty, not started.** Phase 1 does not change the kernel. Kicksecure's hardened kernel is used as-is.

When this work starts, the kernel build must keep every hardening option that Kicksecure enables. `dm-raw-to-iso` checks the boot config for kernel hardening arguments and stops the build if they are missing.
