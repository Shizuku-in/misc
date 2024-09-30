import os
import ezodf

def search(fpath, keyword):
    for root, dirs, files in os.walk(fpath):
        for file in files:
            if file.endswith(".ods"):
                doc_path = os.path.join(root, file)
                doc = ezodf.opendoc(doc_path)
                for sheet in doc.sheets:
                    for row in sheet.rows():
                        data = [str(cell.value).strip() if cell.value is not None else '' for cell in row]
                        if any(keyword.lower() in data.lower() for data in data):
                            prow = [content.replace("密码：", "?pwd=").replace(" ", "") if "密码：" in content else content for content in data] 
                            prow[1] = prow[1].split('}')[1] if '}' in prow[1] else prow[1]
                            prow = [item for item in prow if item]
                            print(f"{prow}") #print(f"Found in {doc_path}, Sheet '{sheet.name}':\n{prow}")

if __name__ == "__main__":
    fpath = "D:\松鼠的礼物"
    keyword = input("搜索内容: ")
    search(fpath, keyword)