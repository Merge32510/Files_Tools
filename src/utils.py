# src/utils.py

from pathlib import Path
from typing import Set

# --- 核心工具函数 ---

def format_file_size(file_path: Path) -> str:
    """
    计算文件大小并转换为保留2位小数的大写单位字符串 (KB, MB)，保留小数点。
    """
    try:
        size_bytes = file_path.stat().st_size
    except FileNotFoundError:
        return "N/A"
        
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f}MB"

def get_unique_path(destination_path: Path) -> Path:
    """
    解决重名冲突：如果目标路径已存在，自动追加 _1, _2
    """
    if not destination_path.exists():
        return destination_path

    stem = destination_path.stem
    suffix = destination_path.suffix
    parent = destination_path.parent
    
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1

def case_insensitive_replace(original_string: str, target_str: str, replacement_str: str) -> str:
    """
    执行不区分大小写的替换（仅替换第一次出现）。
    """
    lower_original = original_string.lower()
    lower_target = target_str.lower()
    
    start_index = lower_original.find(lower_target)
    
    if start_index == -1:
        return original_string
    
    # 构造新的字符串: 匹配前部分 + 替换字符串 + 匹配后部分
    new_string = (
        original_string[:start_index] + 
        replacement_str + 
        original_string[start_index + len(target_str):]
    )
    return new_string

def get_available_extensions(folder_path_str: str) -> Set[str]:
    """
    扫描指定目录，返回所有文件的唯一后缀集合 (小写，带点，例如: {'.jpg', '.png'})。
    """
    folder_path = Path(folder_path_str)
    if not folder_path.is_dir():
        return set()
        
    extensions = set()
    for item in folder_path.iterdir():
        if item.is_file():
            # 获取后缀，转小写，并添加到集合
            ext = item.suffix.lower()
            if ext: # 确保不是没有后缀的文件
                extensions.add(ext)
                
    return extensions