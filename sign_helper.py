"""
swapData 桥接 —— 必须用 32 位 Python 运行 (PvpAlive.dll 是 32 位)。

用法:
    python32/python.exe sign_helper.py "<inner_json>"
    e.g.
    python32/python.exe sign_helper.py '{"randnum":"927942","ts":"1779593748","data":"access_token=...&cup_id=0&match_id=...","version":1}'

输出: 仅一行 ASCII 签名 (hex string)
"""
import ctypes
import os
import sys

DLL_PATH = r"D:\ProgramFile\game\perfectworld\plugin\PvpAlive.dll"


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: sign_helper.py <inner_json>\n")
        return 2
    inner = sys.argv[1].encode("utf-8")

    # 切到 PvpAlive 所在目录，避免缺失同目录依赖时加载失败
    dll_dir = os.path.dirname(DLL_PATH)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(dll_dir)
    cwd = os.getcwd()
    try:
        os.chdir(dll_dir)
        dll = ctypes.WinDLL(DLL_PATH)
    finally:
        os.chdir(cwd)

    # 签名: int __cdecl swapData(const char* in, unsigned in_len, char* out, unsigned* out_len)
    swap = dll.swapData
    swap.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint)]
    swap.restype = ctypes.c_int

    out_buf = ctypes.create_string_buffer(512)
    out_len = ctypes.c_uint(512)
    rv = swap(inner, len(inner), out_buf, ctypes.byref(out_len))
    if not rv:
        sys.stderr.write("swapData returned 0 (failure)\n")
        return 1
    sys.stdout.write(out_buf.value[: out_len.value].decode("utf-8", "replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
