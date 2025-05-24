import os
import zipfile

def zip_folders_in_directory(root_dir):
    if not os.path.isdir(root_dir):
        print("invalid directory path")
        return

    output_dir = os.path.join(root_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    for item in os.listdir(root_dir):
        folder_path = os.path.join(root_dir, item)
        if os.path.isdir(folder_path) and item != "output":
            zip_path = os.path.join(output_dir, f"{item}.zip")
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_STORED) as zipf:
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
            print(f"PACKED: {item} -> {zip_path}")

if __name__ == "__main__":
    user_input = input("input directory: ").strip()
    zip_folders_in_directory(user_input)
