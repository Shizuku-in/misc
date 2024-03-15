import os
import subprocess

def convert(input_dir):
    report = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".wav"):
                wav_path = os.path.join(root, file)
                flac_path = wav_path.rsplit(".", 1)[0] + ".flac"
                subprocess.run(['ffmpeg', '-i', wav_path, '-c:a', 'flac', flac_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                report.append(f"[{wav_path}]--->[{flac_path}]")
            elif file.endswith(".cue"):
                with open(os.path.join(root, file), 'r', encoding='utf-8-sig') as f:
                    lines = f.readlines()
                with open(os.path.join(root, file), 'w', encoding='utf-8-sig') as f:
                    for line in lines:
                        if "FILE" in line and "WAVE" in line:
                            start, end = line.find('"') + 1, line.rfind('"')
                            original = line[start:end]
                            line = line[:start] + original.rsplit('.', 1)[0] + '.flac' + line[end:]
                        f.write(line)
    return report

def generate_report(report, input_dir):
    with open(os.path.join(input_dir, "conversion_report.txt"), 'w', encoding='utf-8') as f:
        for line in report:
            f.write(line + '\n')

if __name__ == "__main__":
    input_directory = input("请输入目录路径: ")
    report = convert(input_directory)
    generate_report(report, input_directory)
    print("转换完成，报告已生成。")
