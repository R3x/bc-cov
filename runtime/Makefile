
bbcov_runtime.bc: bbcov_runtime.c
	clang -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone -o $@ $<

debugbbcov_runtime.bc: bbcov_runtime.c
	clang -emit-llvm -c -g -O0 -Xclang -DDEBUG -disable-O0-optnone -o $@ $<

tracepc_runtime.bc: tracepc_runtime.c
	clang -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone -o $@ $<

debugtracepc_runtime.bc: tracepc_runtime.c
	clang -emit-llvm -c -g -O0 -Xclang -DDEBUG -disable-O0-optnone -o $@ $<

all: bbcov_runtime.bc debugbbcov_runtime.bc tracepc_runtime.bc debugtracepc_runtime.bc

clean:
	rm -f bbcov_runtime.bc debugbbcov_runtime.bc tracepc_runtime.bc debugtracepc_runtime.bc