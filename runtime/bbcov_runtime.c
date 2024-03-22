#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <unistd.h>
#include <signal.h>
#include <assert.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <err.h>
#include <execinfo.h>

int grill_guard_after[100] = {0};
FILE *cov_fp = NULL;
int grill_guard_before[100] = {0};
int done = 0;

void bc_dump_cov();
void bc_cov_set_signal_handler();
//#ifdef GRILLER
void grill_hook_destroy();
//#endif
void _bc_dump_cov();

__attribute__((constructor)) void bc_init_cov()
{
  // read the environment variable bc_COV_FILE
  // if it is set, then open the file and store the file descriptor
  // in a global variable
  // if it is not set, then create default.bc_cov
  // and store the file descriptor in a global variable

  char *bc_cov_file = getenv("BC_COV_FILE");
  if (bc_cov_file == NULL)
  {
    bc_cov_file = "default.bc_cov";
  }
#ifdef DEBUG
  printf("bc_cov_file: %s\n", bc_cov_file);
#endif
  // open the file
  // if the file exists, delete it
  if (access(bc_cov_file, F_OK) != -1)
  {
    remove(bc_cov_file);
  }

  cov_fp = fopen(bc_cov_file, "w");
  bc_cov_set_signal_handler();

  alarm(5);
}

#define PATHMAX 100
#define MAX_STACK_FRAMES 64
static void *stack_traces[MAX_STACK_FRAMES];
static uint8_t alternate_stack[SIGSTKSZ];

void bc_cov_set_signal_handler()
{
  /* setup alternate stack */
  {
    stack_t ss = {};
    ss.ss_sp = (void *)alternate_stack;
    ss.ss_size = SIGSTKSZ;
    ss.ss_flags = 0;

    if (sigaltstack(&ss, NULL) != 0)
    {
      err(1, "sigaltstack");
    }
  }

  /* register our signal handlers */
  {
    struct sigaction sig_action = {};
    sig_action.sa_sigaction = bc_dump_cov;
    sigemptyset(&sig_action.sa_mask);

    sig_action.sa_flags = SA_SIGINFO | SA_ONSTACK;

    if (sigaction(SIGALRM, &sig_action, NULL) != 0)
    {
      err(1, "sigaction");
    }
    if (sigaction(SIGSEGV, &sig_action, NULL) != 0)
    {
      err(1, "sigaction");
    }
    if (sigaction(SIGFPE, &sig_action, NULL) != 0)
    {
      err(1, "sigaction");
    }
    if (sigaction(SIGINT, &sig_action, NULL) != 0)
    {
      err(1, "sigaction");
    }
    if (sigaction(SIGILL, &sig_action, NULL) != 0)
    {
      err(1, "sigaction");
    }
    if (sigaction(SIGTERM, &sig_action, NULL) != 0)
    {
      err(1, "sigaction");
    }
    if (sigaction(SIGABRT, &sig_action, NULL) != 0)
    {
      err(1, "sigaction");
    }
  }
}

__attribute__((destructor)) void bc_dump_cov()
{
  if (done == 1) exit(-1);
  done = 1;
//#ifdef GRILLER
  grill_hook_destroy();
//#endif
  _bc_dump_cov();
  fclose(cov_fp);
  exit(-1);
}

void bc_cov_set_file(char *file_name, int file_name_len, int num_funcs)
{
  // if the file descriptor is not set, then set it
  // else close the file descriptor and set it
  fwrite(&file_name_len, sizeof(int), 1, cov_fp);
  fwrite(file_name, sizeof(char), file_name_len, cov_fp);
  fwrite(&num_funcs, sizeof(int), 1, cov_fp);
}

void bc_cov(char *func_name, int func_name_len, u_int64_t *cov_array, int cov_array_len)
{
  // write the function name to the file
  // write the coverage array to the file
#ifdef DEBUG
  printf("func: %s | ", func_name);
#endif
  fwrite(&func_name_len, sizeof(int), 1, cov_fp);
  fwrite(func_name, sizeof(char), func_name_len, cov_fp);
#ifdef DEBUG
  for (int i = 0; i < cov_array_len; i++)
  {
    printf("%lu,", cov_array[i]);
  }
  printf("\n");
#endif
  fwrite(&cov_array_len, sizeof(int), 1, cov_fp);
  fwrite(cov_array, sizeof(u_int64_t), cov_array_len, cov_fp);
}