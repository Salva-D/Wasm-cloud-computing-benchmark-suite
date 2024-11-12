### Comand to compile
    $CC threads.c -pthread --target=wasm32-wasi-threads -Wl,--import-memory,--export-memory,--max-memory=67108864 -o threads.wasm
- Use wasi-sdk: https://github.com/WebAssembly/wasi-sdk
- Necessary flags found here: https://bytecodealliance.org/articles/wasi-threads
### Comand to run
    wasmtime -S threads threads.wasm
I have lost the webpage where I found out about the -S flag.