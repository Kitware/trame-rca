// Duplicate an NT handle out of another process with DuplicateHandle.
// Requires PROCESS_DUP_HANDLE on the target (e.g. it is our child, running as the same user).
const koffi = require('koffi');

const kernel32 = koffi.load('kernel32.dll');
const OpenProcess = kernel32.func('uintptr_t __stdcall OpenProcess(uint32_t access, int inherit, uint32_t pid)');
const GetCurrentProcess = kernel32.func('uintptr_t __stdcall GetCurrentProcess()');
const DuplicateHandle = kernel32.func('int __stdcall DuplicateHandle(uintptr_t srcProcess, uintptr_t src, uintptr_t dstProcess, _Out_ uintptr_t *dst, uint32_t access, int inherit, uint32_t options)');
const CloseHandle = kernel32.func('int __stdcall CloseHandle(uintptr_t handle)');
const GetLastError = kernel32.func('uint32_t __stdcall GetLastError()');

const PROCESS_DUP_HANDLE = 0x0040;
const DUPLICATE_SAME_ACCESS = 0x2;

const dupHandleFromProcess = (pid, remoteHandle) => {
  const proc = OpenProcess(PROCESS_DUP_HANDLE, 0, pid);
  if (!proc) throw new Error(`OpenProcess(${pid}) failed: error ${GetLastError()}`);
  try {
    const out = [0];
    if (!DuplicateHandle(proc, remoteHandle, GetCurrentProcess(), out, 0, 0, DUPLICATE_SAME_ACCESS)) {
      throw new Error(`DuplicateHandle(${pid}, 0x${remoteHandle.toString(16)}) failed: error ${GetLastError()}`);
    }
    return out[0];
  } finally {
    CloseHandle(proc);
  }
};

// sharedTexture wants the HANDLE value in a Buffer.
const handleBuffer = (handle) => {
  const buf = Buffer.alloc(8);
  buf.writeBigUInt64LE(BigInt(handle));
  return buf;
};

const closeHandle = (handle) => CloseHandle(handle);

module.exports = { dupHandleFromProcess, handleBuffer, closeHandle };
