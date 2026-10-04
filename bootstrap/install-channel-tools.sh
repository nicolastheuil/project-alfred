#!/bin/bash
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
platform_root="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
lock="$platform_root/config/channel-dependencies.lock.json"
node_version=$(jq -r '.node.version' "$lock")
node_url=$(jq -r '.node.url' "$lock")
node_hash=$(jq -r '.node.sha256' "$lock")
stage=$(mktemp -d /var/cache/alfred/channel-install.XXXXXX)
trap 'rm -rf -- "$stage"' EXIT
curl --fail --silent --show-error --location --retry 3 --output "$stage/node.tar.xz" "$node_url"
printf '%s  %s\n' "$node_hash" "$stage/node.tar.xz" | sha256sum --check
if [[ ! -x "/opt/alfred/tools/node-$node_version/bin/node" ]]; then
  tar --extract --file "$stage/node.tar.xz" --directory "$stage" --no-same-owner
  mv "$stage/node-v$node_version-linux-arm64" "/opt/alfred/tools/node-$node_version"
fi
[[ $("/opt/alfred/tools/node-$node_version/bin/node" --version) == "v$node_version" ]]
ln -sfn "/opt/alfred/tools/node-$node_version" /opt/alfred/tools/node
bridge=/opt/alfred/bridges/whatsapp
install -d -m 0755 "$bridge"
cp /opt/alfred/current/scripts/whatsapp-bridge/{package.json,package-lock.json,bridge.js,allowlist.js,outbound_ids.js,owner_message_gate.js,bridge_helpers.js} "$bridge/"
cd "$bridge"
PATH="/opt/alfred/tools/node/bin:$PATH" npm ci --prefix "$bridge" --workspaces=false --ignore-scripts --omit=dev --no-audit --no-fund
sha256sum "$bridge/package.json" | cut -c1-16 | tr -d '\n' > "$bridge/node_modules/.hermes-pkg-hash"
chmod -R go-w "$bridge/node_modules"
curl --fail --silent --show-error --location --output "$stage/1password.asc" https://downloads.1password.com/linux/keys/1password.asc
printf '%s  %s\n' 'f39e7dd9dedc581ced85732832f217e0de5860a3b80279b5af4bc7c6d8157bae' "$stage/1password.asc" | sha256sum --check
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends gnupg
gpg --batch --yes --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg "$stage/1password.asc"
printf '%s\n' 'deb [arch=arm64 signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/arm64 stable main' > /etc/apt/sources.list.d/1password.list
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "1password-cli=$(jq -r .onepassword.version "$lock")"
op --version
