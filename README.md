# OpenNetLab Emulator with GCC

## Installation

```
# Install depot tools and fetch chromium
$ git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
$ export DEPOT_TOOLS_HOME=/path/to/depot_tools
# NOTE: DEPOT_TOOLS_HOME should locate at the front of the PATH
$ export PATH=:$DEPOT_TOOLS_HOME:$PATH
$ git config --global core.autocrlf false
$ git config --global core.filemode false
$ fetch chromium
$ cd src && sudo ./build/install-build-deps.sh

# Install mahimahi
$ sudo apt-get -y install mahimahi

# Get the code and install required packages
$ git clone git@github.com:OpenNetLab/onl-emu.git
$ cd onl-emu && pip install -r requirements.txt
$ export EMU_GYM_PATH=/path/to/onl-emu

# Compile AlphaRTC with GCC and the video call app
$ cd .. && ./r3net-build.sh

# Emulator evaluation of RL-based CC (onnx checkpoint):
$ python runner.py --mode eval --gcc --total-episodes 1 --trace-type simple
