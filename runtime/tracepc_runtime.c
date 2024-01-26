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
#include <sys/mman.h>
#include <fcntl.h>

int done = 0;
int fd = 0;
int curr_offset = 0;
char *map = NULL;

void bc_cov_set_signal_handler();
void bc_dump_cov();

#define MAX_FILE_SIZE 10000

__attribute__((constructor)) void bc_init_cov(void) {
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

  bc_cov_set_signal_handler();
  
  fd = open(bc_cov_file, O_CREAT | O_RDWR, 0666);
  if (fd == -1) {
      perror("Error opening file");
      exit(-1);
      return;
  }

  if (ftruncate(fd, MAX_FILE_SIZE) == -1) {
      perror("Error setting file size");
      close(fd);
      exit(-1);
      return;
  }

  map = mmap(0, MAX_FILE_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  if (map == MAP_FAILED) {
      perror("Error mapping file");
      close(fd);
      exit(-1);
      return; 
  }
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
  grill_hook_destroy();
  if (munmap(map, MAX_FILE_SIZE) == -1) {
      perror("Error unmapping file");
  }

  if (msync(map, MAX_FILE_SIZE, MS_SYNC) == -1) {
      perror("Error syncing file");
  }
  close(fd);
  exit(-1);
}


void bc_cov(uint32_t bbid) {
  ((int *) map)[curr_offset++] = bbid;
}