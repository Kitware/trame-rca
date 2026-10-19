// Duplicate a file descriptor out of another process with pidfd_getfd(2).
// Requires ptrace access to the target (e.g. it is our child with ptrace_scope=1).
const koffi = require('koffi');

const libc = koffi.load('libc.so.6');
const syscall = libc.func('long syscall(long nr, ...)');
const close = libc.func('int close(int fd)');
const strerror = libc.func('const char *strerror(int errnum)');

// x86_64 / asm-generic syscall numbers
const SYS_pidfd_open = 434;
const SYS_pidfd_getfd = 438;

const check = (ret, what) => {
  const r = Number(ret);
  if (r < 0) {
    const errno = koffi.errno();
    throw new Error(`${what} failed: ${strerror(errno)} (errno ${errno})`);
  }
  return r;
};

const dupFdFromProcess = (pid, targetFd) => {
  const pidfd = check(syscall(SYS_pidfd_open, 'int', pid, 'uint', 0), `pidfd_open(${pid})`);
  try {
    return check(syscall(SYS_pidfd_getfd, 'int', pidfd, 'int', targetFd, 'uint', 0), `pidfd_getfd(${pid}, ${targetFd})`);
  } finally {
    close(pidfd);
  }
};

const closeFd = (fd) => close(fd);

module.exports = { dupFdFromProcess, closeFd };
