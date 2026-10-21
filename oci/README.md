![o,age](https://i.postimg.cc/fL6MStSP/derivative-maker-logo6.png)

With the convenience of an engine agnostic debian:trixie container, `derivative-maker-oci` automatically builds Whonix/Kicksecure images, incorporating the official derivative-maker build scripts, while including environment variables and intuitive ways to customize every available build option, container behavior and final build command.  All necessary files already ship with the current derivative-maker source code, allowing for quick and simple deployment with a variety of pre-defined user scripts. The container image is assembled by buildah which grants compatibility with virtually any engine. Additionally, its sources are pinned to the same snapshot.debian.org timestamp a `--freshness frozen` build uses, so the builder and built image use the same packages during reproducible builds.

## Roadmap
- [x] Read documentation
- [ ] Install container engine
- [ ] Clone derivative-maker
- [ ] Container image
- [ ] Choose container parameters
- [ ] Craft a build command
- [ ] Deploy the container
    - [ ] Standard
    - [ ] Custom


## Script Overview
|  Name                                             | Description              | Location
| --------------------------------------------------| -------------------------|------------|
| derivative-maker-oci-image | Assembles the container image | host:derivative-maker/oci
| derivative-maker-oci-run| Creates volumes and starts the container | host:derivative-maker/oci
| derivative-maker-oci-bootstrap| Sets up a lightweight debian environment  | container:/usr/bin

## Usage
- [x] Install container engine
- [x] Cloning derivative-maker
- [x] (Re)build the container image

### Container Image
1. Locate your [desired tag](https://github.com/Whonix/derivative-maker/tags)
2. Clone it
   ```sh
   git clone --depth=1 --branch 17.3.9.9-stable --jobs=4 --recurse-submodules --shallow-submodules https://github.com/Whonix/derivative-maker.git
   ```
3. Install `buildah` and a container engine of your choice. (Example: podman)
   ```sh
   sudo apt-get install -y buildah podman
   ```
5. Execute the build command. Supported engines: `docker` `podman` `nerdctl` `colima` `buildah`.
* The default engine is currently podman, which launches automatically.
   ```sh
   ./derivative-maker-oci-run -- ./derivative-maker <build arguments>
   ```
* Other candidates can be used by passing `ENGINE=<engine>` before running `derivative-maker-oci-run`. (Example: docker)
   ```sh
    ENGINE=docker ./derivative-maker-oci-run -- ./derivative-maker <build arguments>
   ```
* Logs can be generated on the host if required.
  ```sh
   ./derivative-maker-oci-run -- ./derivative-maker <build arguments> 2>&1 | tee -a <log-location>
   ```

### Containerization with Buildah
* Buildah builds container images differently than traditional engines. Instead of spinning up a background daemon and executing a static Dockerfile, Buildah assembles layers using standard bash commands directly on the host file system, configures runtime metadata, unmounts the VFS, and commits the state as an OCI compliant image. All modern container engines are compatible with this format.
* Once Buildah produces the image on disk, it exists inside Buildah's localized local storage. `buildah push ... docker-archive:/dev/stdout` translates this local OCI-formatted image storage structure into a standardized tarball archive on the fly and streams it to standard output, which is then loaded into the privileged space of the user's container engine of choice.
* Apart from other advantages during the initial build process, this allows practically limitless compatibility with any engine, as long as unique sync and load commands are provided to handle the image.

### Multi-arch builds (arm64, amd64, ...)
The build script is arch-agnostic: `from debian:trixie-slim` is a multi-arch
manifest list, and arch-specific packages (e.g. `grub-efi-arm64`,
`grub-efi-amd64`) are pulled in by `build-steps.d/1100_sanity-tests` at
**build time** based on `--arch`, not baked into the image. To target a
specific platform, simply populate global variable TARGET_ARCH=<arch> with your desired architecture before executing ./derivative-docker-oci-run.
```sh
TARGET_ARCH=arm64  ./derivative-maker-oci-run -- ./derivative-maker <build arguments>
```
On Apple Silicon hosts, the default platform already matches
(`linux/arm64`); no extra flags needed. Cross-arch builds require
`qemu-user-static` registered with binfmt_misc.

### Volumes
1. By default three folders are generated in the user's home directory
   ```sh
   BINARY_VOLUME="$HOME/binary_mnt"
   CACHER_VOLUME="$HOME/approx_cache_mnt"
   KEY_VOLUME="$HOME/.key_mnt"
   ```
  + `BINARY_VOLUME` is the location of build artifacts and logs
  + `CACHER_VOLUME` is the mount point of the container's `/var/cache/apt-cacher-ng`
  * `KEY_VOLUME` is the mount point of the container's `/home/user/.gnupg`
2. To change folder names or locations use the container params `--*-mount`

### Container parameters
- [x] Choose container parameters
- [x] (Optional) Add custom volumes

|  Option     | Description              | Sample Value
| ------------| -------------------------|------------|
| `--binary-mount` | Configure custom binary artifact directory | /home/user/whonix/dm-binary
| `--cacher-mount` | Configure custom package cache directory | /home/user/whonix/apt-cache
| `--key-mount` | Configure custom keystore directory | /home/user/whonix/keys

The command to run in the container is explicit, after `--`.

#### Sample Commands
1. Build a Kicksecure or Whonix image
   ```sh
   ./derivative-maker-oci-run -- ./derivative-maker <build arguments>
   ```
2. Execute a specific build-step
   ```sh
  ENGINE=nerdctl ./derivative-maker-oci-run -- build-steps.d/4310_convert-raw-to-iso <build arguments>
   ```
3. Run a custom command (e.g. an interactive shell)
   ```sh
  ENGINE=docker ./derivative-maker-oci-run -- bash
   ```
4. Choose custom volume mount points
   ```sh
   ALLOW_UNFROZEN=true ./derivative-maker-oci-run --binary-mount /home/user/whonix/dm-binary --cacher-mount /home/user/whonix/apt-cache -- ./derivative-maker <build arguments>
   ```

#### Hints
* Multiple custom commands can be chained with `&&` or `;`
* Using end of options `--` is recommended

### Build Command
- [x] Read the [Build Documentation](https://www.whonix.org/wiki/Dev/Build_Documentation/VM#Build)
- [x] Craft a build command

#### Mandatory Build Parameters
1. Target

 | Build Target  | Comment | Image Type |
 | -------------------------|------------|-----|
 | VirtualBox | `.vdi` | `--target virtualbox` |
 | KVM | `.qcow2` |  `--target qcow2`   |
 | RAW | `.raw` |  `--target raw`   |
 | UTM  | `.raw`  |  `--target utm`   |
 | ISO  | `.iso` |   `--target iso`   |

 2. Flavor

 | Flavor Name  | Flavor Parameter |
 | -------------------------|------------|
 | Whonix-Gateway CLI | `--flavor whonix-gateway-cli` |
 | Whonix-Gateway LXQt | `--flavor whonix-gateway-lxqt ` |
 | Whonix-Workstation CLI  | `--flavor whonix-workstation-cli` |
 | Whonix-Workstation LXQt 	  | `--flavor whonix-workstation-lxqt`  |
