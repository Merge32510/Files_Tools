import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
import shutil
import os
from typing import Callable, Dict, Any, List

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

# --- 文件处理器类 (封装核心逻辑) ---

class FileProcessor:
    def __init__(self, source_folder: str, output_folder: str):
        self.source_folder = Path(source_folder)
        self.output_folder = Path(output_folder)
        
        # 确保输出目录存在
        if not self.output_folder.exists():
            self.output_folder.mkdir(parents=True)

        self.files: List[Path] = sorted([f for f in self.source_folder.iterdir() if f.is_file()], key=lambda x: x.name)
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
                if mode == 'a': # 模式 A: 字符替换/删除 (原 A)
                    target = config['target']
                    replace_with = config['replace']
                    scope = config['scope']
                    new_stem = current_stem
                    new_suffix = current_suffix

                    if scope in ['1', '3']: # 文件名主体
                        new_stem = case_insensitive_replace(current_stem, target, replace_with)
                    if scope in ['2', '3']: # 文件后缀
                        new_suffix = case_insensitive_replace(current_suffix, target, replace_with)
                        
                    new_name = f"{new_stem}{new_suffix}"
                
                elif mode == 'b': # 模式 B: 重新命名 (大小/序列) (原 C)
                    if config['type'] == 'size':
                        # 文件名主体只使用格式化后的大小
                        size_str = format_file_size(src_file)
                        new_name = f"{size_str}{current_suffix}" 
                        
                    elif config['type'] == 'sequence':
                        current_num = sequence_counter + index
                        padding = len(str(self.total_files + sequence_counter - 1))
                        num_str = str(current_num).zfill(padding)
                        # 保持：序号_原名.后缀 (序列模式建议保留原名辅助区分)
                        new_name = f"{num_str}_{current_stem}{current_suffix}"
                
                else:
                    log_func(f"❌ 未知模式: {mode}")
                    continue

                # --- 执行文件移动和重命名 ---
                dest_path = self.output_folder / new_name
                final_dest_path = get_unique_path(dest_path)
                
                # 使用 shutil.move 执行原子性的移动/重命名
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

# --- Tkinter GUI 界面 ---

class RenamerApp:
    def __init__(self, master):
        self.master = master
        master.title("文件批量处理器")
        
        # 路径变量
        self.source_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="")
        
        # 模式变量 (初始值改为 'a' - 字符替换/删除)
        self.mode_var = tk.StringVar(value='a')
        
        # 模式 A (原 A) 变量
        self.target_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.scope_var = tk.StringVar(value='1')
        
        # 模式 B (原 C) 变量
        self.type_var = tk.StringVar(value='sequence')
        self.start_num_var = tk.StringVar(value='1')

        # 构建界面
        self.create_widgets()
        self.update_mode_frame() 

    def create_widgets(self):
        # 整体框架
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill='both', expand=True)

        # 1. 路径选择
        path_frame = ttk.LabelFrame(main_frame, text="📁 路径设置", padding="10")
        path_frame.pack(fill='x', pady=5)
        
        # 源目录
        ttk.Label(path_frame, text="源文件目录:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.source_path, width=40, state='readonly').grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="选择源目录", command=lambda: self.select_path('source')).grid(row=0, column=2, padx=5, pady=2)

        # 输出目录
        ttk.Label(path_frame, text="输出结果目录:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.output_path, width=40, state='readonly').grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(path_frame, text="选择输出目录", command=lambda: self.select_path('output')).grid(row=1, column=2, padx=5, pady=2)
        
        # 2. 模式选择
        mode_select_frame = ttk.LabelFrame(main_frame, text="🔧 操作模式选择", padding="10")
        mode_select_frame.pack(fill='x', pady=5)

        modes = [
            ("模式 A: 字符替换/删除", 'a'),
            # ("模式 B: 文件名前后添加字符", 'b'), <--- 已删除
            ("模式 B: 重新命名 (大小/序列)", 'b') # <--- 重新编号为 B
        ]
        
        for i, (text, mode) in enumerate(modes):
            rb = ttk.Radiobutton(mode_select_frame, text=text, variable=self.mode_var, value=mode, command=self.update_mode_frame)
            rb.grid(row=0, column=i, sticky='w', padx=10)

        # 3. 模式参数区域 (动态内容)
        self.mode_params_frame = ttk.LabelFrame(main_frame, text="⚙️ 模式参数", padding="10")
        self.mode_params_frame.pack(fill='x', pady=5)
        
        # 4. 执行按钮
        self.run_button = ttk.Button(main_frame, text="🚀 开始处理", command=self.run_process, state='disabled')
        self.run_button.pack(fill='x', pady=10)
        
        # 5. 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="📝 操作日志", padding="10")
        log_frame.pack(fill='both', expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, state='disabled', wrap='word')
        self.log_text.pack(fill='both', expand=True)
        
        # 路径初始检查
        self.check_paths()
    
    def select_path(self, path_type: str):
        """打开文件夹选择对话框"""
        initial_dir = Path.home()
        
        if path_type == 'source':
            selected_path = filedialog.askdirectory(title="请选择源文件所在的文件夹", initialdir=initial_dir)
            if selected_path:
                self.source_path.set(selected_path)
        elif path_type == 'output':
            selected_path = filedialog.askdirectory(title="请选择输出结果保存的文件夹", initialdir=initial_dir)
            if selected_path:
                self.output_path.set(selected_path)
            elif self.source_path.get():
                default_output = Path(self.source_path.get()) / "Processed"
                self.output_path.set(str(default_output))
        
        self.check_paths()

    def check_paths(self):
        """检查路径是否都已设置，并启用/禁用运行按钮"""
        if self.source_path.get() and self.output_path.get():
            self.run_button.config(state='normal')
        else:
            self.run_button.config(state='disabled')

    def update_mode_frame(self):
        """根据当前模式动态加载参数输入控件"""
        # 清空现有控件
        for widget in self.mode_params_frame.winfo_children():
            widget.destroy()
            
        current_mode = self.mode_var.get()
        
        if current_mode == 'a':
            # 模式 A: 替换与删除 (原 A)
            ttk.Label(self.mode_params_frame, text="旧字符 (支持大小写不敏感查找):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
            ttk.Entry(self.mode_params_frame, textvariable=self.target_var, width=20).grid(row=0, column=1, sticky='ew', padx=5, pady=5)
            ttk.Label(self.mode_params_frame, text="新字符 (留空则删除):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
            ttk.Entry(self.mode_params_frame, textvariable=self.replace_var, width=20).grid(row=1, column=1, sticky='ew', padx=5, pady=5)
            
            ttk.Label(self.mode_params_frame, text="作用范围:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
            scope_frame = ttk.Frame(self.mode_params_frame)
            scope_frame.grid(row=2, column=1, sticky='w', padx=5, pady=5)
            ttk.Radiobutton(scope_frame, text="主体", variable=self.scope_var, value='1').pack(side='left')
            ttk.Radiobutton(scope_frame, text="后缀", variable=self.scope_var, value='2').pack(side='left', padx=10)
            ttk.Radiobutton(scope_frame, text="主体+后缀", variable=self.scope_var, value='3').pack(side='left')

        elif current_mode == 'b':
            # 模式 B: 重新命名 (原 C)
            ttk.Label(self.mode_params_frame, text="命名规则:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
            type_frame = ttk.Frame(self.mode_params_frame)
            type_frame.grid(row=0, column=1, sticky='w', padx=5, pady=5)
            
            # **绑定 command: 切换时触发动态显示/隐藏**
            ttk.Radiobutton(type_frame, text="按文件大小", variable=self.type_var, value='size', command=self.toggle_start_num).pack(side='left')
            ttk.Radiobutton(type_frame, text="按数字序列", variable=self.type_var, value='sequence', command=self.toggle_start_num).pack(side='left', padx=10)
            
            # 数字序列起始值（先创建，但尚未布局）
            self.start_num_label = ttk.Label(self.mode_params_frame, text="起始数字:")
            self.start_num_entry = ttk.Entry(self.mode_params_frame, textvariable=self.start_num_var, width=5)
            
            # **初始化时调用：确保首次加载时状态正确**
            self.toggle_start_num()

    def toggle_start_num(self):
        """控制模式B下起始数字的动态显示/隐藏"""
        if self.type_var.get() == 'sequence':
            # 仅在选择 'sequence' 时使用 grid 显示
            self.start_num_label.grid(row=1, column=0, sticky='w', padx=5, pady=5)
            self.start_num_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        else:
            # 在选择 'size' 时使用 grid_forget 隐藏
            self.start_num_label.grid_forget()
            self.start_num_entry.grid_forget()

    def log_message(self, message: str):
        """向日志框添加消息"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END) 
        self.log_text.config(state='disabled')

    def get_config(self, mode: str) -> Dict[str, Any]:
        """根据当前模式获取配置字典，并进行基础校验"""
        config: Dict[str, Any] = {}
        if mode == 'a': # 模式 A: 字符替换/删除
            config['target'] = self.target_var.get()
            config['replace'] = self.replace_var.get()
            config['scope'] = self.scope_var.get()
            if not config['target']:
                    raise ValueError("模式 A: '旧字符' 不能为空。")
        elif mode == 'b': # 模式 B: 重新命名 (大小/序列)
            config['type'] = self.type_var.get()
            if config['type'] == 'sequence':
                try:
                    # 获取并校验起始数字
                    start_num = int(self.start_num_var.get())
                    if start_num <= 0:
                            raise ValueError("模式 B: '起始数字' 必须是大于零的整数。")
                    config['start_num'] = start_num
                except ValueError as e:
                    raise ValueError(f"模式 B: '起始数字' 必须是整数。错误详情: {e}")
        return config

    def run_process(self):
        """执行按钮绑定的主逻辑"""
        source_path_str = self.source_path.get()
        output_path_str = self.output_path.get()
        current_mode = self.mode_var.get()
        
        # 清空日志
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log_message("--- 开始处理 ---")
        
        try:
            config = self.get_config(current_mode)
            
            processor = FileProcessor(source_path_str, output_path_str)
            
            if processor.total_files == 0:
                self.log_message("🚨 源目录下没有找到任何文件，操作中止。")
                messagebox.showinfo("完成", "源目录下没有找到任何文件。")
                return

            self.log_message(f"共找到 {processor.total_files} 个文件，开始执行...")
            
            # 执行处理
            success_count = processor.process_files(current_mode, config, self.log_message)
            
            self.log_message(f"\n🎉 全部完成！已处理 {success_count} 个文件。")
            self.log_message(f"📁 文件已保存至: {output_path_str}")
            messagebox.showinfo("完成", f"文件批量处理成功！\n已处理 {success_count} 个文件。\n文件已保存至: {output_path_str}")
            
        except ValueError as ve:
            self.log_message(f"参数错误: {ve}")
            messagebox.showerror("参数错误", str(ve))
        except Exception as e:
            self.log_message(f"致命错误: {e}")
            messagebox.showerror("致命错误", f"处理过程中发生致命错误：{e}")


if __name__ == "__main__":
    # 使用 ctypes 解决高分辨率屏幕上的显示模糊问题 (Windows)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    root = tk.Tk()
    app = RenamerApp(root)
    root.mainloop()