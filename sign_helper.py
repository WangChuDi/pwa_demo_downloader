"""
swapData 桥接 —— 必须用 32 位 Python 运行 (PvpAlive.dll 是 32 位)。

用法:
    python32/python.exe sign_helper.py <PvpAlive.dll 绝对路径> "<inner_json>"

输出: 仅一行 ASCII 签名 (hex string)
"""
import ctypes
import os
import sys


def main() -> int:
    if len(sys.argv) != 3:
        sys.stderr.write("usage: sign_helper.py <dll_path> <inner_json>\n")
        return 2
    dll_path = sys.argv[1]
    inner = sys.argv[2].encode("utf-8")

    # 切到 PvpAlive 所在目录，避免缺失同目录依赖时加载失败
    dll_dir = os.path.dirname(dll_path)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(dll_dir)
    cwd = os.getcwd()
    try:
        os.chdir(dll_dir)
        dll = ctypes.WinDLL(dll_path)
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
