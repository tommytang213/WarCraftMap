"""Bound a single owner-initiated Windows process tree to a timeout.

No service, remote control, detached process or global process-name kill. The
initial process is suspended until assigned to a kill-on-close Job Object;
children inherit that job. Closing it also handles launcher early exit/Ctrl-C.
Imported only by the opt-in local adapter, never used by Linux CI.
"""
import ctypes
from ctypes import wintypes as w
import subprocess
import time


def run(argv: list[str], cwd: str, timeout: int) -> dict:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)

    class Startup(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("reserved", w.LPWSTR), ("desktop", w.LPWSTR), ("title", w.LPWSTR),
                    ("x", w.DWORD), ("y", w.DWORD), ("xSize", w.DWORD), ("ySize", w.DWORD),
                    ("xChars", w.DWORD), ("yChars", w.DWORD), ("fill", w.DWORD), ("flags", w.DWORD),
                    ("show", w.WORD), ("reservedSize", w.WORD), ("reserved2", ctypes.c_void_p),
                    ("stdin", w.HANDLE), ("stdout", w.HANDLE), ("stderr", w.HANDLE)]

    class Process(ctypes.Structure):
        _fields_ = [("process", w.HANDLE), ("thread", w.HANDLE), ("pid", w.DWORD), ("tid", w.DWORD)]

    class BasicLimits(ctypes.Structure):
        _fields_ = [("processTime", ctypes.c_longlong), ("jobTime", ctypes.c_longlong), ("flags", w.DWORD),
                    ("minWorking", ctypes.c_size_t), ("maxWorking", ctypes.c_size_t), ("activeLimit", w.DWORD),
                    ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]

    class Limits(ctypes.Structure):
        _fields_ = [("basic", BasicLimits), ("io", ctypes.c_ulonglong * 6),
                    ("processMemory", ctypes.c_size_t), ("jobMemory", ctypes.c_size_t),
                    ("peakProcess", ctypes.c_size_t), ("peakJob", ctypes.c_size_t)]

    class Accounting(ctypes.Structure):
        _fields_ = [("times", ctypes.c_longlong * 4), ("pageFaults", w.DWORD),
                    ("total", w.DWORD), ("active", w.DWORD), ("terminated", w.DWORD)]

    signatures = {
        "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
        "SetInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
        "CreateProcessW": ([w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, w.BOOL, w.DWORD,
                            ctypes.c_void_p, w.LPCWSTR, ctypes.POINTER(Startup), ctypes.POINTER(Process)], w.BOOL),
        "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
        "ResumeThread": ([w.HANDLE], w.DWORD),
        "QueryInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
        "TerminateProcess": ([w.HANDLE, w.UINT], w.BOOL),
        "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
        "CloseHandle": ([w.HANDLE], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        function = getattr(kernel, name); function.argtypes = args; function.restype = result

    def check(value):
        if not value: raise ctypes.WinError(ctypes.get_last_error())
        return value

    job = check(kernel.CreateJobObjectW(None, None))
    process, startup, limits = Process(), Startup(), Limits()
    startup.cb = ctypes.sizeof(startup)
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway
    assigned = False
    try:
        check(kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        command = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
        check(kernel.CreateProcessW(argv[0], command, None, None, False, 0x4, None,
                                    cwd, ctypes.byref(startup), ctypes.byref(process)))  # CREATE_SUSPENDED
        check(kernel.AssignProcessToJobObject(job, process.process)); assigned = True
        if kernel.ResumeThread(process.thread) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        deadline = time.monotonic() + timeout
        while True:
            counts = Accounting()
            check(kernel.QueryInformationJobObject(job, 1, ctypes.byref(counts), ctypes.sizeof(counts), None))
            if counts.active == 0:
                return {"processStarted": True, "timedOut": False}
            if time.monotonic() >= deadline:
                return {"processStarted": True, "timedOut": True}
            time.sleep(0.2)
    finally:
        if process.process and not assigned:
            kernel.TerminateProcess(process.process, 1)
        if assigned:
            kernel.TerminateJobObject(job, 1)
            # Allow child file handles to close before the adapter removes its
            # scratch. KILL_ON_JOB_CLOSE remains a fallback on any API failure.
            cleanup_deadline = time.monotonic() + 5
            while time.monotonic() < cleanup_deadline:
                counts = Accounting()
                if not kernel.QueryInformationJobObject(job, 1, ctypes.byref(counts), ctypes.sizeof(counts), None) or not counts.active:
                    break
                time.sleep(0.1)
        kernel.CloseHandle(job)
        for handle in (process.thread, process.process):
            if handle: kernel.CloseHandle(handle)
