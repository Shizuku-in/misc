import os
import shutil
import subprocess
import argparse
from tqdm import tqdm
from colorama import init, Fore, Style

init(autoreset=True)  # 自动重置颜色

def find_targets(root_dir):
    targets = []
    for dirpath, _, filenames in os.walk(root_dir):
        epub_files = [f for f in filenames if f.lower().endswith('.epub')]
        opf_files = [f for f in filenames if f.lower().endswith('.opf')]

        if not epub_files or not opf_files:
            continue

        for epub_file in epub_files:
            epub_base = os.path.splitext(epub_file)[0]
            matched_opf = None

            # 完全匹配
            for opf_file in opf_files:
                if os.path.splitext(opf_file)[0] == epub_base:
                    matched_opf = opf_file
                    break

            # 模糊匹配（前缀、去掉作者名等）
            if not matched_opf:
                for opf_file in opf_files:
                    if epub_base in opf_file or os.path.splitext(opf_file)[0] in epub_base:
                        matched_opf = opf_file
                        break

            if matched_opf:
                targets.append((dirpath, epub_file, matched_opf))
            else:
                print(Fore.YELLOW + f"[跳过] 无法匹配 OPF：{epub_file} in {dirpath}")

    return targets

def log_message(message, logfile):
    print(message)
    if logfile:
        with open(logfile, 'a', encoding='utf-8') as f:
            f.write(message + '\n')

def embed_metadata_to_epub(targets, backup=False, logfile=None):
    for dirpath, epub_file, opf_file in tqdm(targets, desc="处理进度", unit="本"):
        epub_path = os.path.join(dirpath, epub_file)
        opf_path = os.path.join(dirpath, opf_file)

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
    parser = argparse.ArgumentParser(
        description="将 Calibre 导出的 metadata.opf 元数据嵌入同目录的 EPUB 文件中",
        formatter_class=argparse.RawTextHelpFormatter
    )
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
