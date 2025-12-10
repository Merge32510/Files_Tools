# src/processor.py

from pathlib import Path
import shutil
from typing import Callable, Dict, Any, List
# 从 utils 模块导入需要的辅助函数
from .utils import format_file_size, get_unique_path, case_insensitive_replace 

# --- 文件处理器类 (封装核心逻辑) ---

class FileProcessor:
    def __init__(self, source_folder: str, output_folder: str, extensions: List[str]):
        self.source_folder = Path(source_folder)
        self.output_folder = Path(output_folder)
        self.extensions = extensions 
        
        # 确保输出目录存在
        if not self.output_folder.exists():
            self.output_folder.mkdir(parents=True)

        def is_target_file(f: Path) -> bool:
            if not f.is_file():
                return False
            if not self.extensions: 
                return True
            
            file_ext = f.suffix.lower() 
            return file_ext in self.extensions

        self.files: List[Path] = sorted([f for f in self.source_folder.iterdir() if is_target_file(f)], key=lambda x: x.name)
        self.total_files = len(self.files)

    def process_files(self, mode: str, config: Dict[str, Any], log_func: Callable[[str], None]) -> int:
        """主处理函数，根据模式和配置执行操作"""
        if not self.files:
            return 0

        success_count = 0
        sequence_counter = config.get('start_num', 1) 
        
        for index, src_file in enumerate(self.files):
            try:
                old_name = src_file.name
                current_stem = src_file.stem
                current_suffix = src_file.suffix
                new_name = old_name 
                
                # --- 根据模式生成新文件名 ---
                if mode == 'a': # 模式 A: 字符替换/删除
                    target = config['target']
                    replace_with = config['replace']
                    scope = config['scope']
                    new_stem = current_stem
                    new_suffix = current_suffix

                    if scope in ['1', '3']: 
                        new_stem = case_insensitive_replace(current_stem, target, replace_with)
                    if scope in ['2', '3']: 
                        new_suffix = case_insensitive_replace(current_suffix, target, replace_with)
                        
                    new_name = f"{new_stem}{new_suffix}"
                
                elif mode == 'b': # 模式 B: 重新命名 (大小/序列)
                    if config['type'] == 'size':
                        size_str = format_file_size(src_file)
                        new_name = f"{size_str}{current_suffix}" 
                        
                    elif config['type'] == 'sequence':
                        current_num = sequence_counter + index
                        padding = len(str(self.total_files + sequence_counter - 1))
                        num_str = str(current_num).zfill(padding)
                        new_name = f"{num_str}_{current_stem}{current_suffix}"
                
                else:
                    log_func(f"❌ 未知模式: {mode}")
                    continue

                # --- 执行文件移动和重命名 ---
                dest_path = self.output_folder / new_name
                final_dest_path = get_unique_path(dest_path)
                
                shutil.move(str(src_file), str(final_dest_path))
                
                # 记录操作日志
                if old_name != final_dest_path.name:
                    log_msg = f"✅ [{index+1}/{self.total_files}] 改名: {old_name} -> {final_dest_path.name}"
                else:
                    log_msg = f"📦 [{index+1}/{self.total_files}] 归档: {old_name} (未触发改名)"
                
                log_func(log_msg)
                    
                success_count += 1
                
            except Exception as e:
                log_msg = f"❌ 处理失败: {src_file.name}, 错误: {e}"
                log_func(log_msg)

        return success_count