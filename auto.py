import os
import shutil
import sys
import re

def main():
    if len(sys.argv) != 2:
        print("使用方法：python program.py \"目录路径\"")
        return

    root_dir = sys.argv[1]

    print(f"根目录: {root_dir}")
    print("-" * 50)

    for folder_name in os.listdir(root_dir):
        folder_path = os.path.join(root_dir, folder_name)

        if os.path.isdir(folder_path) and re.match(r"\d{4}年.*", folder_name):
            print(f"▶ 正在处理: {folder_name}")

            sub1 = os.path.join(folder_path, folder_name)  # 同名子文件夹
            sub2 = os.path.join(folder_path, "会社合集")

            for sub in [sub1, sub2]:
                if os.path.exists(sub):
                    print(f"  ├─ 发现子文件夹: {sub}")
                    for item in os.listdir(sub):
                        s = os.path.join(sub, item)
                        d = os.path.join(folder_path, item)
                        print(f"    ├─ 移动: {s}  ->  {d}")
                        shutil.move(s, d)
                    os.rmdir(sub)
                    print(f"  └─ 已删除空文件夹: {sub}")

            new_name = re.sub(r"^\d{4}年", "", folder_name)
            new_folder = os.path.join(root_dir, new_name)
            os.rename(folder_path, new_folder)
            print(f"✔ 已重命名: {folder_path}  ->  {new_folder}")
            print("-" * 50)

    print("所有操作已完成！")

if __name__ == "__main__":
    main()
