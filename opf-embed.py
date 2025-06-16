import os
import shutil
import subprocess
import argparse
from tqdm import tqdm
from colorama import init, Fore, Style

init(autoreset=True)

def find_targets(root_dir):
    targets = []
    for dirpath, _, filenames in os.walk(root_dir):
        if 'metadata.opf' in filenames:
            epub_files = [f for f in filenames if f.lower().endswith('.epub')]
            if len(epub_files) == 1:
                targets.append((dirpath, epub_files[0]))
            elif len(epub_files) > 1:
                print(Fore.YELLOW + f"[跳过] {dirpath} 中有多个 EPUB 文件")
            else:
                print(Fore.YELLOW + f"[跳过] {dirpath} 中未找到 EPUB 文件")
    return targets

def log_message(message, logfile):
    print(message)
    if logfile:
        with open(logfile, 'a', encoding='utf-8') as f:
            f.write(message + '\n')

def embed_metadata_to_epub(targets, backup=False, logfile=None):
    for dirpath, epub_file in tqdm(targets, desc="处理进度", unit="本"):
        epub_path = os.path.join(dirpath, epub_file)
        opf_path = os.path.join(dirpath, 'metadata.opf')

        if backup:
            backup_path = epub_path + ".bak.epub"
            try:
                shutil.copy2(epub_path, backup_path)
                log_message(Fore.CYAN + f"[备份] {epub_file} → {os.path.basename(backup_path)}", logfile)
            except Exception as e:
                log_message(Fore.RED + f"[备份失败] {epub_file}: {e}", logfile)

        try:
            result = subprocess.run(
                ['ebook-meta', epub_path, '--from-opf', opf_path],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8'
            )
            log_message(Fore.GREEN + f"[成功] {epub_file.ljust(40)} ✅", logfile)
        except subprocess.CalledProcessError as e:
            log_message(Fore.RED + f"[失败] {epub_file.ljust(40)} ❌", logfile)
            log_message(Fore.LIGHTRED_EX + f"        错误输出: {e.stderr.strip()}", logfile)
        except UnicodeDecodeError as ue:
            log_message(Fore.RED + f"[编码错误] {epub_file.ljust(40)} ❌", logfile)
            log_message(Fore.LIGHTRED_EX + f"        错误详情: {ue}", logfile)

def main():
    parser = argparse.ArgumentParser(description="将 metadata.opf 嵌入同目录的 EPUB 文件中")
    parser.add_argument("directory", help="包含 EPUB 的主目录")
    parser.add_argument("-l", "--log", help="将日志保存到指定文件")
    parser.add_argument("-b", "--backup", action="store_true", help="备份原始 EPUB 文件")

    args = parser.parse_args()

    print(Style.BRIGHT + f"📂 开始扫描目录：{args.directory}")
    targets = find_targets(args.directory)
    print(f"🔍 共找到 {len(targets)} 本待处理的 EPUB\n")

    if args.log:
        with open(args.log, 'w', encoding='utf-8') as f:
            f.write("📘 EPUB 元数据嵌入日志\n\n")

    embed_metadata_to_epub(targets, backup=args.backup, logfile=args.log)
    print(Style.BRIGHT + Fore.CYAN + "\n📘 全部处理完成！")

if __name__ == '__main__':
    main()
