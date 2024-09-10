#!/bin/bash
# (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.
# shellcheck disable=all
source "$(dirname "$0")/run_step.sh"
source "$(dirname "$0")/environment_setup.sh"

# This makes cython a command line compiler.
export PATH=${CURR_INSTALL_REPO}/bin:${PATH}:${HOME}/local/cython/bin
# Double check we got this right.
which cython || {
  echo_abort "cython not setup correctly"
}

activate_venv() {
  pushd $PYTORCH_INSTALL
  . ${PYTORCH_INSTALL}_env/bin/activate
}

install_ffmpeg_devel() (
  set -euo pipefail
  sudo dnf install -y ffmpeg-free-devel.x86_64
)

install_imageio() (
  set -euo pipefail
  export https_proxy=http://fwdproxy:8080
  pip install imageio
  pip install imageio[pyav]
)

wind_down() {
  deactivate
  popd
}

activate_venv || echo_abort "Failed to activate venv"
run_step install_ffmpeg_devel
run_step install_imageio
wind_down || echo_abort "Failed to reset environment"
