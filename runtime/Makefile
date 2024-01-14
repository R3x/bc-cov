
runtime.bc: runtimelib.c
	clang -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone -o $@ $<

debugruntime.bc: runtimelib.c
	clang -emit-llvm -c -g -O0 -Xclang -DDEBUG -disable-O0-optnone -o $@ $<

all: runtime.bc debugruntime.bc

clean:
	rm -f runtime.bc debugruntime.bc