# Coverage runtime bitcode. CLANG must emit LLVM bitcode compatible with the
# toolchain bccov links against (LLVM-16 here). Override with `make CLANG=...`.
# Default prefers clang-16 / the llvm-16 path, then falls back to bare clang.
CLANG ?= $(shell command -v clang-16 || (test -x /usr/lib/llvm-16/bin/clang && echo /usr/lib/llvm-16/bin/clang) || command -v clang)

bbcov_runtime.bc: bbcov_runtime.c
	$(CLANG) -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone -o $@ $<

debugbbcov_runtime.bc: bbcov_runtime.c
	$(CLANG) -emit-llvm -c -g -O0 -DDEBUG -Xclang -disable-O0-optnone -o $@ $<

tracepc_runtime.bc: tracepc_runtime.c
	$(CLANG) -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone -o $@ $<

debugtracepc_runtime.bc: tracepc_runtime.c
	$(CLANG) -emit-llvm -c -g -O0 -DDEBUG -Xclang -disable-O0-optnone -o $@ $<

all: bbcov_runtime.bc debugbbcov_runtime.bc tracepc_runtime.bc debugtracepc_runtime.bc

clean:
	rm -f bbcov_runtime.bc debugbbcov_runtime.bc tracepc_runtime.bc debugtracepc_runtime.bc
