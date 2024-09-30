import os
import re
import requests
from bs4 import BeautifulSoup
import urllib.parse
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

def search_vgmdb(album_name, results, not_found, index, progress_var):
    search_url = f"https://vgmdb.net/search?q={urllib.parse.quote(album_name)}&field=title"
    try:
        response = requests.get(search_url, allow_redirects=True, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        not_found.append(f"{album_name} (请求失败: {str(e)})")
        progress_var.set(progress_var.get() + 1)
        return
    if "album" in response.url:
        album_id = re.search(r'/album/(\d+)', response.url)
        if album_id:
            results[index] = (album_name, album_id.group(1))
        else:
            not_found.append(album_name)
    else:
        soup = BeautifulSoup(response.content, 'html.parser')
        search_results = soup.find_all('div', class_='albumtitle')
        for result in search_results:
            link = result.find('a')
            album_id = re.search(r'/album/(\d+)', link['href'])
            album_title = link.text.strip()
            if album_name.lower() in album_title.lower():
                results[index] = (album_name, album_id.group(1))
                break
        else:
            not_found.append(album_name)
    progress_var.set(progress_var.get() + 1)

# 扫描
def scan_folders(path, user_pattern):
    folders = []
    try:
        pattern = re.compile(user_pattern)
    except re.error:
        messagebox.showerror("正则表达式错误", "无效的正则表达式")
        return folders
    
    for folder_name in os.listdir(path):
        if os.path.isdir(os.path.join(path, folder_name)):
            match = pattern.match(folder_name)
            if match:
                folders.append(match.group(1))
    return folders

# 选择路径1时调用
def select_folder():
    folder_path.set(filedialog.askdirectory())

# 选择路径2时调用
def select_save_path():
    save_path.set(filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")]))
    if not save_path.get():
        save_path.set("album_ids.txt")

# 多线程
def threaded_search(folders):
    threads = []
    results = [None] * len(folders)
    not_found = []
    progress_var.set(0)
    progress_bar['maximum'] = len(folders)
    for index, folder in enumerate(folders):
        t = threading.Thread(target=search_vgmdb, args=(folder, results, not_found, index, progress_var))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    display_results(results, not_found)

# 显示结果并保存
def display_results(results, not_found):
    output_text.delete(1.0, tk.END)
    found = [res for res in results if res is not None]
    
    if found:
        output_text.insert(tk.END, "已找到的专辑ID:\n")
        for album_name, album_id in found:
            output_text.insert(tk.END, f"{album_name}: {album_id}\n")
        output_text.insert(tk.END, "\nID表：\n")
        for _, album_id in found:
            output_text.insert(tk.END, album_id + "\n")
    if not_found:
        output_text.insert(tk.END, "\n未找到的专辑:\n")
        for folder in not_found:
            output_text.insert(tk.END, folder + "\n")

    save_file_path = save_path.get()
    with open(save_file_path, "w", encoding='utf-8') as f:
        if found:
            f.write("已找到: \n")
            for album_name, album_id in found:
                f.write(f"{album_name}: {album_id}\n")
            f.write("\nID　Sheet:\n")
            for _, album_id in found:
                f.write(f"{album_id}\n")
        if not_found:
            f.write("\n未找到的专辑:\n")
            for folder in not_found:
                f.write(folder + "\n")

    messagebox.showinfo("完成", f"处理完成，结果已导出到 {save_file_path}")

# 开始扫描时调用
def start_scan():
    path = folder_path.get()
    user_pattern = regex_pattern.get()
    if not os.path.exists(path):
        messagebox.showerror("错误", "路径不存在")
        return
    folders = scan_folders(path, user_pattern)
    if not folders:
        messagebox.showinfo("结果", "未找到符合条件的文件夹")
        return

    threading.Thread(target=threaded_search, args=(folders,)).start()

# Main
root = tk.Tk()
root.title("VGMdb ID Scanner")

root.geometry("600x550")

# Input
folder_path = tk.StringVar()
regex_pattern = tk.StringVar(value=r"\[\d{6}(?: \(\w+\))?\] (.+)")
save_path = tk.StringVar(value="album_ids.txt")

# Layout
tk.Label(root, text="指定路径:").pack(pady=10)
tk.Entry(root, textvariable=folder_path, width=50).pack(pady=5)
tk.Button(root, text="选择路径", command=select_folder).pack()

tk.Label(root, text="正则表达式:").pack(pady=10)
tk.Entry(root, textvariable=regex_pattern, width=50).pack(pady=5)

tk.Label(root, text="保存位置:").pack(pady=10)
tk.Entry(root, textvariable=save_path, width=50).pack(pady=5)
tk.Button(root, text="选择路径", command=select_save_path).pack()

tk.Button(root, text="开始", command=start_scan).pack(pady=20)

tk.Label(root, text="结果:").pack(pady=5)

# Text Scrollbar
output_frame = tk.Frame(root)
output_frame.pack(pady=10)

output_text = tk.Text(output_frame, height=10, width=70, wrap="none")
output_text.pack(side=tk.LEFT, fill=tk.BOTH)

scrollbar = tk.Scrollbar(output_frame, orient="vertical", command=output_text.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

output_text.config(yscrollcommand=scrollbar.set)

# Progressbar
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
progress_bar.pack(pady=10)

root.mainloop()
