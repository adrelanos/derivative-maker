#!/bin/bash

## Static check: every theme/asset path configured by the DhampirOS defaults
## must exist in the tracked source-rootfs payload, and the QTerminal colour
## scheme must match the palette.

set -o errexit
set -o nounset
set -o pipefail

readonly -- SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly -- PKG_DIR="${SCRIPT_DIR}/.."
readonly -- ROOTFS="${PKG_DIR}/assets/source-rootfs"
readonly -- SKEL="${ROOTFS}/etc/skel/.config"
readonly -- PALETTE="${PKG_DIR}/source-meta/palette.json"

declare -i failures=0

## Print the value of KEY from an ini-style file.
config_value() {
  local -- file="$1"
  local -- key="$2"
  sed -n "s/^${key}=//p" -- "$file" | head -n 1
}

## Print the value of KEY inside [SECTION] of an ini-style file.
section_value() {
  local -- file="$1"
  local -- section="$2"
  local -- key="$3"
  awk -v sec="[${section}]" -v key="${key}" '
    $0 == sec { in_sec = 1; next }
    /^\[/ { in_sec = 0 }
    in_sec && index($0, key "=") == 1 { sub(/^[^=]*=/, ""); print; exit }
  ' "$file"
}

## Fail unless the absolute install path exists in the payload.
require_path() {
  local -- label="$1"
  local -- install_path="$2"
  if [[ -z "${install_path}" ]]; then
    printf 'MISSING %s: no value configured\n' "${label}" >&2
    failures+=1
  elif [[ ! -e "${ROOTFS}${install_path}" ]]; then
    printf 'MISSING %s: %s\n' "${label}" "${install_path}" >&2
    failures+=1
  else
    printf 'ok %s: %s\n' "${label}" "${install_path}"
  fi
}

## Print the hex value of a named token from palette.json.
palette_token() {
  local -- name="$1"
  grep -oE "\"${name}\": \"#[0-9A-Fa-f]{6}\"" -- "${PALETTE}" | grep -oE '#[0-9A-Fa-f]{6}'
}

## Convert #RRGGBB to the R,G,B form used by .colorscheme files.
hex_to_rgb() {
  local -- hex="${1#\#}"
  printf '%d,%d,%d' "0x${hex:0:2}" "0x${hex:2:2}" "0x${hex:4:2}"
}

## Check the QTerminal colour scheme against palette.json.
check_colour_scheme() {
  local -- scheme="$1"
  local -- scheme_file="${ROOTFS}/usr/share/qtermwidget6/color-schemes/${scheme}.colorscheme"
  local -a hexes=()
  local -- section
  local -- i
  local -- expected
  local -- actual

  mapfile -t hexes < <(sed -n '/"ansi"/,/\]/p' -- "${PALETTE}" | grep -oE '#[0-9A-Fa-f]{6}')
  if [[ "${#hexes[@]}" -ne 16 ]]; then
    printf 'FAIL palette: expected 16 ANSI colours, found %s\n' "${#hexes[@]}" >&2
    failures+=1
    return 0
  fi

  expected="$(hex_to_rgb "$(palette_token ink)")"
  actual="$(section_value "${scheme_file}" Background Color)"
  if [[ "${actual}" != "${expected}" ]]; then
    printf 'FAIL %s Background: %s != ink %s\n' "${scheme}" "${actual}" "${expected}" >&2
    failures+=1
  fi

  expected="$(hex_to_rgb "$(palette_token silver)")"
  actual="$(section_value "${scheme_file}" Foreground Color)"
  if [[ "${actual}" != "${expected}" ]]; then
    printf 'FAIL %s Foreground: %s != silver %s\n' "${scheme}" "${actual}" "${expected}" >&2
    failures+=1
  fi

  for i in {0..15}; do
    if (( i < 8 )); then
      section="Color${i}"
    else
      section="Color$((i - 8))Intense"
    fi
    expected="$(hex_to_rgb "${hexes[i]}")"
    actual="$(section_value "${scheme_file}" "${section}" Color)"
    if [[ "${actual}" != "${expected}" ]]; then
      printf 'FAIL %s %s: %s != palette ansi[%s] %s\n' "${scheme}" "${section}" "${actual}" "${i}" "${expected}" >&2
      failures+=1
    fi
  done
  printf 'ok %s colours match palette.json\n' "${scheme}"
}

lxqt_theme="$(config_value "${SKEL}/lxqt/lxqt.conf" theme)"
icon_theme="$(config_value "${SKEL}/lxqt/lxqt.conf" icon_theme)"
desktop_wallpaper="$(config_value "${SKEL}/pcmanfm-qt/lxqt/settings.conf" Wallpaper)"
terminal_scheme="$(config_value "${SKEL}/qterminal.org/qterminal.ini" colorScheme)"
theme_wallpaper="$(config_value "${ROOTFS}/usr/share/lxqt/themes/${lxqt_theme}/wallpaper.cfg" wallpaper)"

require_path 'LXQt theme' "/usr/share/lxqt/themes/${lxqt_theme}"
require_path 'LXQt theme wallpaper' "${theme_wallpaper}"
require_path 'icon theme index' "/usr/share/icons/${icon_theme}/index.theme"
require_path 'desktop wallpaper' "${desktop_wallpaper}"
require_path 'QTerminal colour scheme' "/usr/share/qtermwidget6/color-schemes/${terminal_scheme}.colorscheme"
check_colour_scheme "${terminal_scheme}"

if (( failures > 0 )); then
  printf '%s configured path(s) failed\n' "${failures}" >&2
  exit 1
fi
printf 'all configured DhampirOS theme paths exist\n'
