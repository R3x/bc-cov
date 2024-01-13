#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>

FILE *cov_fp = NULL;

__attribute__((constructor))
void bc_init_cov() {
    // read the environment variable bc_COV_FILE
    // if it is set, then open the file and store the file descriptor
    // in a global variable
    // if it is not set, then create default.bc_cov
    // and store the file descriptor in a global variable

    char *bc_cov_file = getenv("BC_COV_FILE");
    if (bc_cov_file == NULL) {
        bc_cov_file = "default.bc_cov";
    }   
#ifdef DEBUG
    printf("bc_cov_file: %s\n", bc_cov_file);
#endif
    // open the file
    cov_fp = fopen(bc_cov_file, "w");
}

__attribute__((destructor))
void bc_dump_cov() {
    _bc_dump_cov();
}

void bc_cov_set_file(char *file_name, int file_name_len, int num_funcs) {
    // if the file descriptor is not set, then set it
    // else close the file descriptor and set it
    fwrite(&file_name_len, sizeof(int), 1, cov_fp);
    fwrite(file_name, sizeof(char), file_name_len, cov_fp);
    fwrite(&num_funcs, sizeof(int), 1, cov_fp);
}

void bc_cov(char *func_name, int func_name_len, u_int64_t *cov_array, int cov_array_len) {
    // write the function name to the file
    // write the coverage array to the file
    fwrite(&func_name_len, sizeof(int), 1, cov_fp);
    fwrite(func_name, sizeof(char), func_name_len, cov_fp);
    fwrite(&cov_array_len, sizeof(u_int64_t), 1, cov_fp);
    fwrite( cov_array, sizeof(int), cov_array_len, cov_fp);
}