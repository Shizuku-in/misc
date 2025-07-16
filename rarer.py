import sys
import os
import subprocess

def main():
    if len(sys.argv) != 2:
        print("用法: python script.py <目录>")
        sys.exit(1)

    source_dir = sys.argv[1]

    if not os.path.isdir(source_dir):
        print("错误: 提供的路径不是一个有效目录")
        sys.exit(1)

    compressed_dir = os.path.join(source_dir, "compressed")
    os.makedirs(compressed_dir, exist_ok=True)

    for file_name in os.listdir(source_dir):
        file_path = os.path.join(source_dir, file_name)
        if os.path.isfile(file_path):
            name, ext = os.path.splitext(file_name)
            ext_no_dot = ext[1:] if ext.startswith('.') else ext
            rar_name = f"{name} [NS] ({ext_no_dot}).rar"
            rar_path = os.path.join(compressed_dir, rar_name)

            # rar.exe a -m0 means Store mode (no compression)
            cmd = ["rar", "a", "-m0", rar_path, file_path]
            print(f"正在压缩: {file_name} -> {rar_name}")

            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f"压缩文件时出错: {file_name}")

    print("所有文件已压缩完成。")

if __name__ == "__main__":
    main()
