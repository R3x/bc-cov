#!/bin/bash

# if first argument is "clean"
if [ "$1" == "clean" ]; then
    echo "[*] Trying to clean"
    rm -rf build
fi

# get the current directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

mkdir -p $DIR/build
echo "[*] Trying to Run Cmake"
cd $DIR/build
cmake ..
echo "[*] Trying to make"
make -j$(nproc)

# Build the coverage runtime bitcode (bbcov_runtime.bc, tracepc_runtime.bc, ...).
# bccov's link_runtime fails silently if these are missing, so build them here.
# Honor "clean" by rebuilding from scratch.
echo "[*] Building coverage runtime bitcode"
if [ "$1" == "clean" ]; then
    make -C "$DIR/../runtime" clean
fi
make -C "$DIR/../runtime" all

# Copy all the passes to the build directory