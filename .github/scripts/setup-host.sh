#!/usr/bin/env bash
set -xe

echo "=== Storage profile before cleaning ==="
df -h /
sudo swapoff -a || true
sudo rm -f /mnt/swapfile
sudo rm -rf /usr/share/dotnet /usr/local/lib/android /opt/ghc /opt/hostedtoolcache/CodeQL /usr/local/share/powershell /usr/local/share/chromium
sudo docker image prune --all --force
sudo apt-get remove --purge -y "node*" "php*" "mysql*" "google*" || true
sudo apt-get autoremove -y && sudo apt-get clean

echo "=== Storage profile after aggressive cleaning ==="
df -h /

echo "Expose Host KVM Permissions..."
echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --name-match=kvm

echo "Installing QEMU and Cloud-Init Tools on Host..."
sudo apt-get update && sudo apt-get install -y qemu-system-x86 qemu-utils cloud-image-utils genisoimage netcat-openbsd

echo "Downloading Minimal OS Base & Allocate Space Pool..."
TARGET_URL="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2"
curl -L -o debian-base.qcow2 "$TARGET_URL"
qemu-img resize -f qcow2 debian-base.qcow2 75G
