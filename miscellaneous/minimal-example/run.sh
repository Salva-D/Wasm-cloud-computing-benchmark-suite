#!/usr/bin/sh

clang --target=wasm32 -O3 -nostdlib -Wl,--no-entry -Wl,--export-all -fuse-ld="$WASI_ROOT/wasm-ld" -o foo.wasm foo.c

# python3 -m http.server 3000
