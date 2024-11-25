async function start() {
    const wasm = await WebAssembly.instantiateStreaming(
        fetch("foo.wasm"));
    const exports = wasm.instance.exports
    console.log(exports)
    const after_foo = exports.foo(69)
    console.log(after_foo)
}

start().catch((e) => console.error(e));
