# src/gui.py

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
from typing import Dict, Any, List

# 从同一包内的其他模块导入
from .processor import FileProcessor
from .utils import get_available_extensions

# --- Tkinter GUI 界面 ---

class RenamerApp:
    def __init__(self, master):
        self.master = master
        master.title("文件批量处理器")
        
        # 路径变量
        self.source_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="")
        
        # 扩展名筛选变量
        self.extensions_filter_var = tk.StringVar(value="") 
        
        # 模式变量
        self.mode_var = tk.StringVar(value='a')
        
        # 模式 A 变量
        self.target_var = tk.StringVar()
        self.replace_var = tk.StringVar()
        self.scope_var = tk.StringVar(value='1')
        
        # 模式 B 变量
        self.type_var = tk.StringVar(value='sequence')
        self.start_num_var = tk.StringVar(value='1')

        # 构建界面
        self.create_widgets()
        self.update_mode_frame() 

    def create_widgets(self):
        # 整体框架
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill='both', expand=True)

        # 1. 路径和筛选设置
        path_frame = ttk.LabelFrame(main_frame, text="📁 路径与筛选设置", padding="10")
        path_frame.pack(fill='x', pady=5)
        path_frame.columnconfigure(1, weight=1) 
        
        row_idx = 0
        # 源目录
        ttk.Label(path_frame, text="源文件目录:").grid(row=row_idx, column=0, sticky='w', padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.source_path, width=40, state='readonly').grid(row=row_idx, column=1, sticky='ew', padx=5, pady=2)
        
        select_source_btn = ttk.Button(path_frame, text="选择源目录", command=lambda: self.select_path('source'))
        select_source_btn.grid(row=row_idx, column=2, padx=5, pady=2)

        row_idx += 1
        # 输出目录
        ttk.Label(path_frame, text="输出结果目录:").grid(row=row_idx, column=0, sticky='w', padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.output_path, width=40, state='readonly').grid(row=row_idx, column=1, sticky='ew', padx=5, pady=2)
        ttk.Button(path_frame, text="选择输出目录", command=lambda: self.select_path('output')).grid(row=row_idx, column=2, padx=5, pady=2)
        
        row_idx += 1
        # 扩展名筛选输入框
        ttk.Label(path_frame, text="扩展名筛选 (用逗号分隔，留空处理所有文件):").grid(row=row_idx, column=0, sticky='w', padx=5, pady=2)
        ttk.Entry(path_frame, textvariable=self.extensions_filter_var, width=40).grid(row=row_idx, column=1, sticky='ew', padx=5, pady=2)
        
        # 获取可用后缀按钮
        get_ext_btn = ttk.Button(path_frame, text="获取可用后缀", command=self.get_and_set_extensions)
        get_ext_btn.grid(row=row_idx, column=2, padx=5, pady=2)
        
        # 2. 模式选择
        mode_select_frame = ttk.LabelFrame(main_frame, text="🔧 操作模式选择", padding="10")
        mode_select_frame.pack(fill='x', pady=5)

        modes = [
            ("模式 A: 字符替换/删除", 'a'),
            ("模式 B: 重新命名 (大小/序列)", 'b')
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
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=10, state='disabled', wrap='word', yscrollcommand=scrollbar.set)
        self.log_text.pack(fill='both', expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        self.check_paths()
    
    def select_path(self, path_type: str):
        """打开文件夹选择对话框"""
        initial_dir = Path.home()
        
        current_path = self.source_path.get() if path_type == 'source' else self.output_path.get()
        if current_path and Path(current_path).is_dir():
             initial_dir = current_path

        selected_path = filedialog.askdirectory(title=f"请选择{'源文件' if path_type == 'source' else '输出结果'}所在的文件夹", initialdir=initial_dir)
        
        if selected_path:
            if path_type == 'source':
                self.source_path.set(selected_path)
                self.get_and_set_extensions() 
            elif path_type == 'output':
                self.output_path.set(selected_path)
        elif path_type == 'output' and self.source_path.get() and not self.output_path.get():
             default_output = Path(self.source_path.get()) / "Processed_Files"
             self.output_path.set(str(default_output))
        
        self.check_paths()

    def get_and_set_extensions(self):
        """获取源目录下的所有文件后缀，并填充到筛选输入框中。"""
        source_dir = self.source_path.get()
        if not source_dir or not Path(source_dir).is_dir():
            # 此时用户可能还未选择源目录，静默退出
            return 
            
        try:
            available_extensions = get_available_extensions(source_dir)
            
            if not available_extensions:
                self.extensions_filter_var.set("")
                self.log_message("⚠️ 目录下未找到任何文件。")
                return

            ext_list_str = ", ".join([f"*{ext}" for ext in available_extensions])
            
            self.extensions_filter_var.set(ext_list_str)
            self.log_message(f"ℹ️ 已将找到的 {len(available_extensions)} 种后缀填充到筛选框。")
            
        except Exception as e:
            self.log_message(f"❌ 获取后缀失败: {e}")
            messagebox.showerror("错误", f"获取可用后缀失败: {e}")


    def check_paths(self):
        """检查路径是否都已设置，并启用/禁用运行按钮"""
        if self.source_path.get() and self.output_path.get():
            self.run_button.config(state='normal')
        else:
            self.run_button.config(state='disabled')

    def update_mode_frame(self):
        """根据当前模式动态加载参数输入控件"""
        for widget in self.mode_params_frame.winfo_children():
            widget.destroy()
            
        current_mode = self.mode_var.get()
        self.mode_params_frame.columnconfigure(1, weight=1)

        if current_mode == 'a':
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
            ttk.Label(self.mode_params_frame, text="命名规则:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
            type_frame = ttk.Frame(self.mode_params_frame)
            type_frame.grid(row=0, column=1, sticky='w', padx=5, pady=5)
            
            ttk.Radiobutton(type_frame, text="按文件大小", variable=self.type_var, value='size', command=self.toggle_start_num).pack(side='left')
            ttk.Radiobutton(type_frame, text="按数字序列", variable=self.type_var, value='sequence', command=self.toggle_start_num).pack(side='left', padx=10)
            
            self.start_num_label = ttk.Label(self.mode_params_frame, text="起始数字:")
            self.start_num_entry = ttk.Entry(self.mode_params_frame, textvariable=self.start_num_var, width=5)
            
            self.toggle_start_num()

    def toggle_start_num(self):
        """控制模式B下起始数字的动态显示/隐藏"""
        if self.type_var.get() == 'sequence':
            self.start_num_label.grid(row=1, column=0, sticky='w', padx=5, pady=5)
            self.start_num_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        else:
            self.start_num_label.grid_forget()
            self.start_num_entry.grid_forget()

    def log_message(self, message: str):
        """向日志框添加消息"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END) 
        self.log_text.config(state='disabled')

    def parse_extensions_filter(self) -> List[str]:
        """
        解析扩展名筛选字符串，返回规范化的扩展名列表 (小写，带点，无重复)。
        """
        filter_str = self.extensions_filter_var.get()
        if not filter_str:
            return []
            
        extensions = set()
        parts = filter_str.split(',')
        for part in parts:
            part = part.strip().lower()
            if not part:
                continue
            
            # 去除前导的 *
            if part.startswith('*'):
                part = part[1:]
            
            # 确保以 . 开头
            if not part.startswith('.'):
                part = '.' + part
                
            if len(part) > 1: # 排除掉只剩下 '.' 的情况
                extensions.add(part)
                
        return sorted(list(extensions))


    def get_config(self, mode: str) -> Dict[str, Any]:
        """根据当前模式获取配置字典，并进行基础校验"""
        config: Dict[str, Any] = {}
        if mode == 'a': 
            config['target'] = self.target_var.get()
            config['replace'] = self.replace_var.get()
            config['scope'] = self.scope_var.get()
            if not config['target']:
                raise ValueError("模式 A: '旧字符' 不能为空。")
        elif mode == 'b': 
            config['type'] = self.type_var.get()
            if config['type'] == 'sequence':
                try:
                    start_num = int(self.start_num_var.get())
                    if start_num <= 0:
                        raise ValueError("模式 B: '起始数字' 必须是大于零的整数。")
                    config['start_num'] = start_num
                except ValueError:
                    raise ValueError(f"模式 B: '起始数字' 必须是整数。当前输入: {self.start_num_var.get()}")
        return config

    def run_process(self):
        """执行按钮绑定的主逻辑"""
        source_path_str = self.source_path.get()
        output_path_str = self.output_path.get()
        current_mode = self.mode_var.get()
        
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log_message("--- 开始处理 ---")
        
        try:
            config = self.get_config(current_mode)
            target_extensions = self.parse_extensions_filter()

            if not Path(source_path_str).is_dir():
                 raise FileNotFoundError("源目录路径无效或不存在。")

            processor = FileProcessor(source_path_str, output_path_str, target_extensions)
            
            if target_extensions:
                self.log_message(f"筛选扩展名: {', '.join(target_extensions)}")

            if processor.total_files == 0:
                self.log_message("🚨 源目录下没有找到符合筛选条件的任何文件，操作中止。")
                messagebox.showinfo("完成", "源目录下没有找到符合筛选条件的任何文件。")
                return

            self.log_message(f"共找到 {processor.total_files} 个文件，开始执行 [模式 {current_mode.upper()}]...")
            
            success_count = processor.process_files(current_mode, config, self.log_message)
            
            self.log_message(f"\n🎉 全部完成！已处理 {success_count} 个文件。")
            self.log_message(f"📁 文件已保存至: {output_path_str}")
            messagebox.showinfo("完成", f"文件批量处理成功！\n已处理 {success_count} 个文件。\n文件已保存至: {output_path_str}")
            
        except (ValueError, FileNotFoundError) as ve:
            self.log_message(f"参数/路径错误: {ve}")
            messagebox.showerror("错误", str(ve))
        except Exception as e:
            self.log_message(f"致命错误: {e}")
            messagebox.showerror("致命错误", f"处理过程中发生致命错误：{e}")