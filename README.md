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
$ git clone --recurse-submodules git@github.com:jeongyooneo/onl-emu-gym.git
$ cd onl-emu-gym && pip install -r requirements.txt
$ cd stable-baselines3 && git checkout sb3-for-rtc && pip install -e .
$ export EMU_GYM_PATH=/path/to/onl-emu-gym

# Compile AlphaRTC with GCC and the video call app
$ cd .. && ./gcc-build.sh

# Emulator evaluation of GCC:
$ python mahimahi-gcc.py --trace-type belgium 2>&1 | tee output
