import os
from PIL import Image

def convert_images_to_jpeg(directory, quality=90, subsampling=0, scale_factor=0.8):
    if not os.path.exists(directory):
        print(f"'{directory}' 不存在")
        return
    convert_dir = os.path.join(directory, 'convert')
    os.makedirs(convert_dir, exist_ok=True)

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        if os.path.isfile(file_path) and filename.lower().endswith(('png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff')):
            with Image.open(file_path) as img:
                new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
                img = img.resize(new_size, Image.LANCZOS)
                img = img.convert('RGB')
                new_filename = os.path.splitext(filename)[0] + '.jpg'
                new_file_path = os.path.join(convert_dir, new_filename)
                img.save(new_file_path, 'JPEG', quality=quality, optimize=True, subsampling=subsampling, progressive=True)
                print(f"已转换：{new_file_path}")
    
    print("已转换")

user_directory = input("路径：")
convert_images_to_jpeg(user_directory, quality=90, subsampling=0, scale_factor=0.7)
