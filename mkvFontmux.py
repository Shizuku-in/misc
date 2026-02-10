#!/usr/bin/env python3

'''
Copyright (C) 2026 gkouen

This work is free. You can redistribute it and/or modify it under the
terms of the Do What The Fuck You Want To Public License, Version 2,
as published by Sam Hocevar. See http://www.wtfpl.net/ for more details.
'''

import os
import sys
import shutil
import argparse
import logging
import subprocess
import re
import secrets
import string
from pathlib import Path
from fontTools.ttLib import TTFont, TTCollection
from fontTools.subset import main as subset_main

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich import box

MKVMERGE_BIN = r"D:\Program Files\MKVToolNixPortable_84.0_azo\MKVToolNixPortable\App\ProgramFiles64\mkvmerge.exe"
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
IGNORE_FONTS = {'default', 'arial', 'sans-serif'}
SMART_SUFFIXES = ['_gbk', '_gb2312', '_big5', '_jis', '_kr']

console = Console()
file_logger = None

def setup_file_logger(save_log_path):
    global file_logger
    if save_log_path:
        file_logger = logging.getLogger("FileLogger")
        file_logger.setLevel(logging.INFO)
        file_logger.handlers.clear()
        fh = logging.FileHandler(save_log_path, mode='w', encoding='utf-8')
        fh.setFormatter(logging.Formatter(LOG_FORMAT))
        file_logger.addHandler(fh)

def log_to_file(msg, level="info"):
    if file_logger:
        if level == "warning":
            file_logger.warning(msg)
        elif level == "error":
            file_logger.error(msg)
        else:
            file_logger.info(msg)

def normalize_font_key(name):
    return name.lower().strip()

def generate_random_name(length=10):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def obfuscate_font_names(font_path, new_family_name):
    try:
        tt = TTFont(font_path)
        name_table = tt['name']
        targets = set()
        for record in name_table.names:
            if record.nameID in (1, 4, 6):
                targets.add((record.platformID, record.platEncID, record.langID))
        for platform_id, plat_enc_id, lang_id in targets:
            name_table.setName(new_family_name, 1, platform_id, plat_enc_id, lang_id)
            name_table.setName(new_family_name, 4, platform_id, plat_enc_id, lang_id)
            name_table.setName(new_family_name, 6, platform_id, plat_enc_id, lang_id)
        tt.save(font_path)
        tt.close()
        return True
    except Exception as e:
        log_to_file(f"[Warning] Failed to update name table: {font_path} ({e})", "warning")
        return False

class FontManager:
    def __init__(self, search_dirs=None, smart_match=True):
        self.font_map = {}
        self.smart_match = smart_match
        self._scan_dirs(search_dirs)

    def _get_system_font_dirs(self):
        if sys.platform == "win32":
            dirs = [os.path.join(os.environ["WINDIR"], "Fonts")]
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                dirs.append(os.path.join(local_appdata, "Microsoft", "Windows", "Fonts"))
            return dirs
        elif sys.platform == "darwin":
            return ["/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
        else:
            return ["/usr/share/fonts", os.path.expanduser("~/.local/share/fonts")]

    def _scan_dirs(self, custom_dirs):
        target_dirs = custom_dirs if custom_dirs else self._get_system_font_dirs()
        log_to_file(f"[System] Start scanning font directories: {target_dirs}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True 
        ) as progress:
            task = progress.add_task(f"[cyan]Scanning fonts...", total=None)
            for d in target_dirs:
                p = Path(d)
                if not p.exists(): continue
                for file_path in p.rglob("*"):
                    if file_path.suffix.lower() in ['.ttf', '.otf', '.ttc']:
                        self._process_font_file(file_path)
                        progress.update(task, description=f"[cyan]Fonts indexed: {len(self.font_map)} names...")
            
            log_to_file(f"[System] Scan complete. Indexed {len(self.font_map)} font names.")
            console.print(f"[green][OK][/] Font index built: [bold cyan]{len(self.font_map)}[/] names.")

    def _process_font_file(self, file_path):
        try:
            abs_path = str(file_path.resolve())
            if file_path.suffix.lower() == '.ttc':
                with TTCollection(file_path) as ttc:
                    for i, _ in enumerate(ttc.fonts):
                        self._register_font(abs_path, i)
            else:
                self._register_font(abs_path, 0)
        except Exception:
            log_to_file(f"[Warning] Failed to read font file: {file_path}", "warning")

    def _register_font(self, file_path, index):
        try:
            tt = TTFont(file_path, fontNumber=index, lazy=True)
            for record in tt['name'].names:
                if record.nameID in (1, 4, 6): 
                    name = record.toUnicode()
                    if name:
                        key = normalize_font_key(name)
                        self.font_map[key] = (file_path, index, name)
                        self.font_map[key.replace(" ", "")] = (file_path, index, name)
            tt.close()
        except Exception:
            log_to_file(f"[Warning] Failed to register font: {file_path}", "warning")

    def find_font(self, ass_name):
        target = normalize_font_key(ass_name)
        if target in self.font_map: return self.font_map[target]
        if self.smart_match:
            for s in SMART_SUFFIXES:
                if target.endswith(s):
                    clean = target.replace(s, "")
                    if clean in self.font_map: return self.font_map[clean]
        return None

class AssParser:
    def __init__(self, filepath):
        self.text_by_font = {}
        self._parse(filepath)

    def _parse(self, filepath):
        with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
            lines = f.readlines()
        styles = {}
        section = None
        for line in lines:
            line = line.strip()
            if line.startswith('['):
                section = line
                continue
            if section == '[V4+ Styles]' and line.startswith('Style:'):
                parts = line.split(',')
                if len(parts) > 2:
                    styles[parts[0].replace('Style:', '').strip()] = parts[1].strip()
        for line in lines:
            if line.startswith('Dialogue:'):
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    style_name = parts[3].strip()
                    font = styles.get(style_name, 'Default')
                    text = re.sub(r'\{.*?\}|\\N|\\n', '', parts[9].strip())
                    self.text_by_font.setdefault(font, set()).update(text)

def subset_font_task(font_path, font_index, text, output_dir, new_family_name, disable_subset=False):
    name = Path(font_path).stem
    if font_index > 0: name += f"_sub{font_index}"
    orig_ext = Path(font_path).suffix.lower()
    out_ext = '.otf' if orig_ext == '.otf' else '.ttf'
    mime = "application/vnd.ms-opentype" if out_ext == '.otf' else "application/x-truetype-font"
    out_path = Path(output_dir) / f"{name}_subset{out_ext}"
    obfuscated_path = Path(output_dir) / f"{name}_{new_family_name}{out_ext}"
    
    if disable_subset:
        log_to_file(f"[Font] Subset disabled. Using original file: {font_path}")
        return str(font_path), mime

    text_str = "".join(text)
    if not text_str: return None, None
    log_to_file(f"[Font] Subsetting: src='{font_path}' index={font_index} -> dst='{out_path}'")
    args = [
        str(font_path), f"--text={text_str}", f"--output-file={str(out_path)}",
        f"--font-number={font_index}", "--layout-features=*", "--name-IDs=*",
    ]
    if orig_ext == '.woff2': args.append("--flavor=woff2")
    try:
        subset_main(args)
        if obfuscate_font_names(str(out_path), new_family_name):
            shutil.move(str(out_path), str(obfuscated_path))
            return str(obfuscated_path), mime
        return str(out_path), mime
    except Exception as e:
        log_to_file(f"[Error] Subset failed {name}: {e}", "error")
        return None, None

def rewrite_ass_files(ass_files, font_name_map, temp_dir):
    if not font_name_map:
        return ass_files

    temp_ass_dir = Path(temp_dir) / "temp_ass"
    temp_ass_dir.mkdir(exist_ok=True)
    rewritten_files = []
    normalized_map = {normalize_font_key(k): v for k, v in font_name_map.items()}

    for ass_path in ass_files:
        with open(ass_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            lines = f.readlines()

        output_lines = []
        in_script_info = False
        inserted_map = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if stripped == "[Script Info]":
                    in_script_info = True
                    inserted_map = False
                else:
                    if in_script_info and not inserted_map:
                        for src, dst in font_name_map.items():
                            output_lines.append(f"; FontMap: {src} -> {dst}\n")
                        inserted_map = True
                    in_script_info = False

            if stripped.startswith("Style:"):
                parts = line.split(',')
                if len(parts) > 2:
                    original = parts[1].strip()
                    replacement = normalized_map.get(normalize_font_key(original))
                    if replacement:
                        parts[1] = replacement
                        line = ",".join(parts)

            if "\\fn" in line:
                def _replace_fn(match):
                    font_name = match.group(1)
                    replacement = normalized_map.get(normalize_font_key(font_name))
                    return f"\\fn{replacement}" if replacement else match.group(0)
                line = re.sub(r"\\fn([^\\}]+)", _replace_fn, line)

            output_lines.append(line)

        if in_script_info and not inserted_map:
            output_lines.append("\n")
            for src, dst in font_name_map.items():
                output_lines.append(f"; FontMap: {src} -> {dst}\n")

        if not any(l.strip() == "[Script Info]" for l in output_lines):
            mapping_lines = ["[Script Info]\n"]
            for src, dst in font_name_map.items():
                mapping_lines.append(f"; FontMap: {src} -> {dst}\n")
            output_lines = mapping_lines + ["\n"] + output_lines

        out_ass = temp_ass_dir / ass_path.name
        with open(out_ass, 'w', encoding='utf-8-sig', errors='ignore') as f:
            f.writelines(output_lines)
        rewritten_files.append(out_ass)

    return rewritten_files

def process_mkv(mkv_path, args, font_manager, temp_dir):
    log_to_file(f"\n{'='*20}\n[File] Start: {mkv_path.absolute()}\n{'='*20}")
    console.print()
    console.rule(f"[bold blue]Processing: {mkv_path.name}[/]")
    base_name = mkv_path.stem
    
    all_ass_files = list(mkv_path.parent.glob("*.ass"))
    ass_files = [f for f in all_ass_files if f.name.lower().startswith(base_name.lower())]
    
    if not ass_files:
        console.print("[yellow]Warning: No matching ASS subtitles found. Skipping.[/]")
        log_to_file("[Warning] No matching ASS subtitles found", "warning")
        return

    log_to_file(f"[Subtitles] Found ASS files: {[f.name for f in ass_files]}")

    needed_fonts = {}
    with console.status("[bold green]Parsing subtitle font usage...", spinner="dots"):
        for ass in ass_files:
            p = AssParser(ass)
            for font, chars in p.text_by_font.items():
                if normalize_font_key(font) in IGNORE_FONTS:
                    continue
                needed_fonts.setdefault(font, set()).update(chars)
    
    log_to_file(f"[Analysis] Required fonts: {list(needed_fonts.keys())}")

    # Report table
    table = Table(title="Font Match Report", box=box.ROUNDED, show_lines=True)
    table.add_column("ASS Font", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Source File", style="dim")
    table.add_column("Char Count", justify="right", style="magenta")

    valid_fonts = [] 

    for font_name, chars in needed_fonts.items():
        info = font_manager.find_font(font_name)
        char_count = len(chars)
        
        if info:
            file_path, font_index, real_name = info
            log_to_file(f"[Match] OK: ASS='{font_name}' -> File='{file_path}'")
            table.add_row(
                font_name, 
                "[green]OK[/]", 
                f"{real_name}\n({Path(file_path).name})", 
                str(char_count)
            )
            valid_fonts.append((font_name, info, chars))
        else:
            log_to_file(f"[Match] Missing in system: '{font_name}'", "warning")
            table.add_row(
                font_name, 
                "[bold red]Missing[/]", 
                "---", 
                str(char_count)
            )

    console.print(table)

    # Only-report modes stop here.
    if args.only_print_matchfont:
        console.print("[dim italic]Font match report only. Skipping remaining steps.[/]")
        log_to_file("[Report] Font match report only. Skipping remaining steps.")
        return
    if args.only_print_fonts:
        console.print("[dim italic]Report only. Skipping subsetting and muxing.[/]")
        log_to_file("[Report] Report only. Skipping remaining steps.")
        return

    if not valid_fonts:
        console.print("[yellow]Warning: No valid fonts to process.[/]")
        return

    attachments = []
    font_name_map = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Generating font subsets...", total=len(valid_fonts))
        for font_name, info, chars in valid_fonts:
            file_path, font_index, _ = info
            random_name = generate_random_name()
            font_name_map[font_name] = random_name
            path, mime = subset_font_task(file_path, font_index, chars, temp_dir, random_name, args.disable_subset)
            if path:
                attachments.append((path, mime))
            progress.advance(task)

    if args.overwrite:
        out_file = temp_dir / f"temp_{mkv_path.name}"
    else:
        out_dir = mkv_path.parent / "output"
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / mkv_path.name

    rewritten_ass_files = rewrite_ass_files(ass_files, font_name_map, temp_dir)

    cmd = [MKVMERGE_BIN, "-o", str(out_file), str(mkv_path)]
    for ass in rewritten_ass_files:
        cmd.extend(["--language", "0:chi", str(ass)])
    for fpath, mime in attachments:
        cmd.extend(["--attachment-mime-type", mime, "--attach-file", fpath])

    log_to_file(f"[Mux] Start: output -> {out_file.absolute()}")

    with console.status("[bold blue]Muxing with mkvmerge...", spinner="earth"):
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            log_to_file(f"[Mux] Completed successfully.")
            if args.overwrite:
                shutil.move(str(out_file), str(mkv_path))
                console.print(f"[bold green]OK: Overwrote {mkv_path.name}[/]")
            else:
                console.print(f"[bold green]OK: Created output/{mkv_path.name}[/]")
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Mux failed.[/]")
            console.print(Panel(e.stderr.decode(), title="Error details", border_style="red"))
            log_to_file(f"[Error] Mux failed: {e.stderr.decode()}", "error")

def main():
    parser = argparse.ArgumentParser(description="MKV font subset + mux tool")
    parser.add_argument("dir", help="Directory containing videos and subtitles")
    parser.add_argument("--force-match", action="store_true", help="Force exact font name matching")
    parser.add_argument("--font-directory", help="Custom font scan directory")
    parser.add_argument("--disable-subset", action="store_true", help="Disable font subsetting")
    parser.add_argument("--save-log", action="store_true", help="Save log to mux.log")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite source MKV")
    parser.add_argument("--remove-temp", action="store_true", help="Remove temporary font files")
    parser.add_argument("--only-print-fonts", action="store_true", help="Report font usage only")
    parser.add_argument("--only-print-matchfont", action="store_true", help="Report font matching only")

    args = parser.parse_args()
    
    work_dir = Path(args.dir.strip('"').strip("'"))
    if not work_dir.exists():
        console.print(f"[bold red]Error: directory not found {work_dir}[/]")
        return

    log_file = work_dir / "mux.log" if args.save_log else None
    setup_file_logger(log_file)

    if not Path(MKVMERGE_BIN).exists():
        console.print(f"[bold red]Error: mkvmerge not found at {MKVMERGE_BIN}[/]")
        return

    # Dynamic title
    if args.only_print_matchfont:
        title_mode = "[bold cyan]Font match mode (report only)[/]"
    elif args.only_print_fonts:
        title_mode = "[bold yellow]Report mode (report only)[/]"
    else:
        title_mode = "[bold green]Mux mode[/]"
    console.print(Panel.fit(f"[bold white]MKV Font Mux Tool[/]\n[dim]Directory: {work_dir}[/]\n{title_mode}", style="blue"))

    font_dirs = [args.font_directory] if args.font_directory else None
    fm = FontManager(search_dirs=font_dirs, smart_match=not args.force_match)

    temp_dir = work_dir / "temp_fonts_mux"
    temp_dir.mkdir(exist_ok=True)

    try:
        mkvs = list(work_dir.glob("*.mkv"))
        if not mkvs:
            console.print("[red]No MKV files found in the directory.[/]")
            
        for mkv in mkvs:
            process_mkv(mkv, args, fm, temp_dir)
            
    finally:
        log_to_file(f"\n[Summary] Task finished.")
        if args.remove_temp and temp_dir.exists():
            shutil.rmtree(temp_dir)
            console.print("[dim]Temporary files removed.[/]")

if __name__ == "__main__":
    main()
