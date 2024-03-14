import os
import chardet
import codecs

def detect_encoding(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read()
    result = chardet.detect(raw)
    return result['encoding']

def convert_encoding_to_utf8_sig(filepath, original):
    with codecs.open(filepath, 'r', original) as file:
        content = file.read()
    with codecs.open(filepath, 'w', 'utf-8-sig') as file:
        file.write(content)

def scan_and_convert(directory):
    report = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.cue'):
                filepath = os.path.join(root, file)
                original = detect_encoding(filepath)
                if original != 'utf-8-sig':
                    convert_encoding_to_utf8_sig(filepath, original)
                    report.append(f"[{file}] [{original}]->[UTF-8-SIG]")
    return report

def main():
    directory = input("目录：")
    report = scan_and_convert(directory)
    reportpath = os.path.join(directory, 'report.txt')
    with open(reportpath, 'w', encoding='utf-8') as reportfile:
        for line in report:
            reportfile.write(line + '\n')
    print(f"报告文件：{reportpath}")
    if not report:
        print("没有找到需要转换的cue文件")

if __name__ == "__main__":
    main()
