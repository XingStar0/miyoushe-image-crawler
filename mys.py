import requests
import os
import time
import re
import json
from typing import Dict, Optional
from tqdm import tqdm
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import platform
from datetime import datetime
import webbrowser  # 添加导入

class MysPostCrawler:
    """
    /**
     * 米游社帖子爬虫
     * @param {string} uid - 用户ID
     * @param {string} base_path - 图片保存基础路径
     */
    """
    def __init__(self, uid: str, base_path: str):
        """
        /**
         * 初始化爬虫
         * @param {string} uid - 用户ID
         * @param {string} base_path - 图片保存基础路径
         */
        """
        self.uid = uid
        self.base_url = "https://bbs-api.miyoushe.com/post/wapi/userPost"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # 验证用户ID是否有效
        if not self.validate_uid():
            raise ValueError("用户ID无效")
            
        # 获取用户名
        self.username = self.get_username()
        # 更新保存路径，加入用户名
        self.save_path = os.path.join(base_path, self.username)
        self.downloader = ImageDownloader(base_path=self.save_path)

    def validate_uid(self) -> bool:
        """
        /**
         * 验证用户ID是否有效
         * @returns {boolean} 用户ID是否有效
         */
        """
        try:
            params = {
                "uid": self.uid,
                "size": 1,
                "offset": ""
            }
            response = requests.get(self.base_url, headers=self.headers, params=params)
            data = response.json()
            
            # 检查响应数据
            if data and "retcode" in data:
                if data["retcode"] == 0:
                    return True
                elif data["retcode"] == -1:  # 通常表示用户不存在
                    return False
            return False
        except Exception:
            return False

    def get_username(self) -> str:
        """
        /**
         * 获取用户名
         * @returns {string} 用户名，如果获取失败则返回用户ID
         */
        """
        try:
            # 获取第一页帖子
            params = {
                "uid": self.uid,
                "size": 1,
                "offset": ""
            }
            response = requests.get(self.base_url, headers=self.headers, params=params)
            data = response.json()
            
            if data and "data" in data and "list" in data["data"] and data["data"]["list"]:
                # 从帖子信息中获取用户名
                username = data["data"]["list"][0]["user"]["nickname"]
                # 替换非法字符
                username = re.sub(r'[\\/:*?"<>|]', '_', username)
                return username
        except Exception:
            pass
        
        return self.uid

    def fetch_page(self, offset: str = "") -> Optional[Dict]:
        """
        /**
         * 获取单页帖子数据
         * @param {string} offset - 偏移量
         * @returns {Optional[Dict]} 帖子数据
         */
        """
        params = {
            "uid": self.uid,
            "size": 20,
            "offset": offset
        }
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers
            )
            data = response.json()
            
            if data["retcode"] != 0:
                print(f"\n请求失败: {data['message']}")
                return None
                
            return data
            
        except Exception as e:
            print(f"\n获取数据出错: {str(e)}")
            return None

    def count_total_posts(self) -> int:
        """
        /**
         * 统计用户总帖子数量
         * @returns {int} 总帖子数
         */
        """
        total_count = 0
        offset = ""
        
        print("正在统计用户帖子总数...")
        while True:
            data = self.fetch_page(offset)
            if not data or "data" not in data:
                break
                
            current_posts = data["data"]["list"]
            total_count += len(current_posts)
            
            if data["data"]["is_last"]:
                break
                
            offset = data["data"]["next_offset"]
            time.sleep(1)
            
        print(f"用户共有 {total_count} 条帖子")
        return total_count

    def process_posts(self):
        """
        /**
         * 处理所有帖子数据并下载图片
         */
        """
        total_count = 0
        downloaded_count = 0
        offset = ""
        
        print("\r已找到 0 条帖子 | 等待开始下载...", end="", flush=True)
        
        try:
            while True:
                data = self.fetch_page(offset)
                if not data or "data" not in data:
                    break
                
                current_posts = data["data"]["list"]
                current_count = len(current_posts)
                total_count += current_count
                
                print(f"\r已找到 {total_count} 条帖子 | 等待开始下载...", end="", flush=True)
                
                for post in current_posts:
                    subject = post['post']['subject']
                    display_subject = subject[:30] + '...' if len(subject) > 30 else subject
                    
                    # 重置下载器的大小计数，获取当前大小
                    current_size = self.downloader.get_size_str()
                    
                    self.process_single_post(post)
                    downloaded_count += 1
                    
                    # 使用格式化字符串，确保每次都是完整替换整行
                    status = f"\r已找到 {total_count} 条帖子 | 正在下载第 {downloaded_count}/{total_count} 条帖子，标题为「{display_subject}」| 已下载 {current_size}"
                    print(status, end="", flush=True)
                
                if data["data"]["is_last"]:
                    break
                
                offset = data["data"]["next_offset"]
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n用户中断下载")
            return
            
        final_size = self.downloader.get_size_str()
        print(f"\n\n下载完成！共处理 {total_count} 条帖子，总大小 {final_size}")

    def process_single_post(self, post: Dict):
        """
        /**
         * 处理单条帖子数据
         * @param {Dict} post - 帖子数据
         */
        """
        if 'image_list' in post and post['image_list']:
            post_id = post['post']['post_id']
            subject = post['post']['subject']
            
            for idx, img in enumerate(post['image_list']):
                if 'url' in img:
                    self.downloader.download_image(
                        url=img['url'],
                        subject=subject,
                        filename=f"{post_id}_{idx}.{img['format'].lower()}"
                    )
                    time.sleep(0.5)

class ImageDownloader:
    """
    /**
     * 图片下载器
     * @param {string} base_path - 图片保存基础路径
     * @param {int} max_retries - 最大重试次数
     */
    """
    def __init__(self, base_path: str, max_retries: int = 3):
        self.base_path = base_path
        self.max_retries = max_retries
        self.total_bytes = 0
        self._create_base_dir()
        self.session = requests.Session()
        retry = requests.adapters.Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retry))

    def _create_base_dir(self) -> None:
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def _create_subject_dir(self, subject: str) -> str:
        clean_subject = re.sub(r'[\\/:*?"<>|]', '_', subject)
        clean_subject = clean_subject[:50]
        subject_path = os.path.join(self.base_path, clean_subject)
        
        if not os.path.exists(subject_path):
            os.makedirs(subject_path)
        return subject_path

    def get_size_str(self) -> str:
        """
        /**
         * 获取人类可读的大小字符串
         * @returns {string} 格式化的大小字符串
         */
        """
        bytes = float(self.total_bytes)
        
        if bytes < 1024:
            return f"{int(bytes)}B"
        elif bytes < 1024 * 1024:
            return f"{bytes/1024:.1f}KB"
        else:
            return f"{bytes/(1024*1024):.1f}MB"

    def add_size(self, bytes_size: int):
        """
        /**
         * 添加文件大小
         * @param {int} bytes_size - 文件字节大小
         */
        """
        self.total_bytes += bytes_size

    def download_image(self, url: str, subject: str, filename: str) -> bool:
        """
        /**
         * 下载单张图片
         * @param {string} url - 图片URL
         * @param {string} subject - 帖子主题
         * @param {string} filename - 文件名
         * @returns {boolean} 下载是否成功
         */
        """
        subject_path = self._create_subject_dir(subject)
        file_path = os.path.join(subject_path, filename)
        
        if os.path.exists(file_path):
            self.add_size(os.path.getsize(file_path))
            return True
            
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url, 
                    timeout=30,
                    verify=True,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )
                
                if response.status_code == 200:
                    content = response.content
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    self.add_size(len(content))
                    return True
                    
            except requests.exceptions.SSLError:
                try:
                    response = self.session.get(
                        url, 
                        timeout=30,
                        verify=False,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                    )
                    
                    if response.status_code == 200:
                        content = response.content
                        with open(file_path, 'wb') as f:
                            f.write(content)
                        self.add_size(len(content))
                        return True
                        
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        print(f"\n下载失败 {url}: {str(e)}")
                    continue
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"\n下载失败 {url}: {str(e)}")
                continue
                
            time.sleep(1)
            
        return False

    def get_total_size(self) -> int:
        """
        /**
         * 获取已下载的总大小
         * @returns {int} 总字节数
         */
        """
        return self.total_bytes

class MysUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("米游社帖子下载器")
        self.root.geometry("600x300")
        
        # 设置窗口居中
        self._center_window()
        
        # 设置窗口最小尺寸
        self.root.minsize(600, 300)
        
        # 创建基础目录
        self.base_dir = "米游社帖子图片下载器"
        self.today = datetime.now().strftime("%Y%m%d")
        self.images_path = None  # 将在获取用户名后设置完整路径
        self.current_user_url = None  # 添加用户URL存储
        self.mys_cos_url = "https://www.miyoushe.com/ys/home/49"  # 米游社cos区固定链接
        
        # 创建变量
        self.uid_var = tk.StringVar()
        self.status_var = tk.StringVar(value="等待开始...")
        self.is_running = False
        self.crawler = None
        
        # 添加用户ID输入变更追踪
        self.uid_var.trace_add("write", self.on_uid_change)
        
        # 设置全局样式
        self._setup_styles()
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_widgets()
        
    def _center_window(self):
        """使窗口居中显示"""
        self.root.update_idletasks()
        width = 600
        height = 300
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def _setup_styles(self):
        """设置控件样式"""
        style = ttk.Style()
        
        if 'clam' in style.theme_names():
            style.theme_use('clam')
            
        style.configure('Custom.TButton',
                       padding=5,
                       font=('微软雅黑', 9))
                       
        style.configure('Custom.TLabel',
                       font=('微软雅黑', 10))
                       
        style.configure('Status.TLabel',
                       font=('微软雅黑', 9))
                       
        # 添加提示标签样式
        style.configure('Hint.TLabel',
                       font=('微软雅黑', 9))
        
    def _create_widgets(self):
        """创建UI组件"""
        # 标题
        title_label = ttk.Label(
            self.main_frame,
            text="米游社帖子下载工具",
            style='Custom.TLabel',
            font=('微软雅黑', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # 用户ID输入框（居中显示）
        frame_input = ttk.Frame(self.main_frame)
        frame_input.pack(fill=tk.X, pady=(0, 15))
        
        # 创建一个容器使输入框居中
        input_container = ttk.Frame(frame_input)
        input_container.pack(anchor=tk.CENTER)
        
        ttk.Label(
            input_container,
            text="用户ID/主页链接:",
            style='Custom.TLabel'
        ).pack(side=tk.LEFT)
        
        self.uid_entry = ttk.Entry(
            input_container,
            textvariable=self.uid_var,
            width=40,  # 增加输入框宽度
            font=('微软雅黑', 10)
        )
        self.uid_entry.pack(side=tk.LEFT, padx=5)
        
        # 添加提示标签
        self.hint_label = ttk.Label(
            frame_input,
            text="支持直接粘贴用户主页链接",
            style='Hint.TLabel',
            foreground='gray'
        )
        self.hint_label.pack(pady=(5, 0))
        
        # 按钮区域
        frame_buttons = ttk.Frame(self.main_frame)
        frame_buttons.pack(fill=tk.X, pady=(0, 15))
        
        # 创建按钮容器使按钮居中
        button_container = ttk.Frame(frame_buttons)
        button_container.pack(anchor=tk.CENTER)
        
        self.start_btn = ttk.Button(
            button_container,
            text="开始下载",
            command=self.start_download,
            style='Custom.TButton',
            width=15
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            button_container,
            text="终止下载",
            command=self.stop_download,
            style='Custom.TButton',
            state=tk.DISABLED,
            width=15
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.open_folder_btn = ttk.Button(
            button_container,
            text="打开下载目录",
            command=self.open_images_folder,
            style='Custom.TButton',
            width=15
        )
        self.open_folder_btn.pack(side=tk.LEFT, padx=5)
        
        # 修改米游社按钮
        self.open_mys_btn = ttk.Button(
            button_container,
            text="打开米游社cos区",  # 修改按钮文字
            command=self.open_mys_cos,  # 修改命令函数
            style='Custom.TButton',
            width=15
        )
        self.open_mys_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态显示区域（带边框）
        status_frame = ttk.LabelFrame(
            self.main_frame,
            text="下载状态",
            padding="10"
        )
        status_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            style='Status.TLabel',
            wraplength=520,
            justify=tk.LEFT
        )
        self.status_label.pack(fill=tk.BOTH, expand=True)
        
    def on_uid_change(self, *args):
        """当用户ID输入变化时触发"""
        input_text = self.uid_var.get().strip()
        
        # 尝试从输入中提取用户ID
        uid = self.extract_uid(input_text)
        if uid and uid != input_text:
            self.uid_var.set(uid)
            self.hint_label.config(
                text=f"已自动提取用户ID: {uid} (点击'打开米游社主页'查看原页面)", 
                foreground='green'
            )
        elif not input_text:
            self.hint_label.config(
                text="支持直接粘贴用户主页链接", 
                foreground='gray'
            )

    def extract_uid(self, text: str) -> Optional[str]:
        """
        从输入文本中提取用户ID
        支持的格式：
        1. 纯数字ID
        2. 主页链接格式1: https://www.miyoushe.com/ys/accountCenter/postList?id=xxx
        3. 主页链接格式2: https://www.miyoushe.com/xxx/home/xxx
        """
        # 如果是纯数字，直接返回
        if text.isdigit():
            return text
            
        # 尝试匹配链接中的ID
        patterns = [
            r'accountCenter/postList\?id=(\d+)',  # 匹配格式1
            r'miyoushe\.com/[^/]+/home/(\d+)',   # 匹配格式2
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # 保存完整URL
                if 'miyoushe.com' in text:
                    self.current_user_url = text
                else:
                    self.current_user_url = f"https://www.miyoushe.com/ys/home/{match.group(1)}"
                return match.group(1)
                
        return None

    def start_download(self):
        """开始下载"""
        uid = self.uid_var.get().strip()
        if not uid:
            self.status_var.set("错误：请输入用户ID或主页链接")
            messagebox.showerror("错误", "请输入用户ID或主页链接")
            return
            
        # 验证输入
        if not uid.isdigit():
            self.status_var.set("错误：请输入正确的用户ID或主页链接")
            messagebox.showerror("错误", "请输入正确的用户ID或主页链接")
            return
            
        # 创建基础路径（日期目录）
        date_path = os.path.join(os.getcwd(), self.base_dir, self.today)
        
        try:
            # 创建爬虫实例（会验证用户ID）
            self.crawler = MysPostCrawler(uid, base_path=date_path)
        except ValueError as e:
            self.status_var.set(f"错误：{str(e)}，请检查用户ID是否正确")
            messagebox.showerror("错误", "用户ID无效，请检查是否输入正确")
            return
        except Exception as e:
            self.status_var.set(f"错误：{str(e)}")
            messagebox.showerror("错误", f"发生错误：{str(e)}")
            return
            
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 更新完整的图片保存路径
        self.images_path = self.crawler.save_path
        
        # 在新线程中运行下载任务
        thread = threading.Thread(target=self.download_task)
        thread.daemon = True
        thread.start()
        
    def stop_download(self):
        """终止下载"""
        self.is_running = False
        self.status_var.set("欢迎再次使用~")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
    def download_task(self):
        """下载任务"""
        try:
            total_count = 0
            downloaded_count = 0
            offset = ""
            
            while self.is_running:
                data = self.crawler.fetch_page(offset)
                if not data or "data" not in data:
                    if "message" in data:
                        error_msg = f"获取数据失败：{data['message']}"
                        self.status_var.set(error_msg)
                        messagebox.showerror("错误", error_msg)
                    break
                
                current_posts = data["data"]["list"]
                current_count = len(current_posts)
                total_count += current_count
                
                self.update_status(f"已找到 {total_count} 条帖子 | 等待开始下载...")
                
                for post in current_posts:
                    if not self.is_running:
                        return
                        
                    subject = post['post']['subject']
                    display_subject = subject[:30] + '...' if len(subject) > 30 else subject
                    
                    self.crawler.process_single_post(post)
                    downloaded_count += 1
                    
                    current_size = self.crawler.downloader.get_size_str()
                    status = f"已找到 {total_count} 条帖子 | 正在下载第 {downloaded_count}/{total_count} 条帖子，标题为「{display_subject}」| 已下载 {current_size}"
                    self.update_status(status)
                
                if data["data"]["is_last"]:
                    break
                    
                offset = data["data"]["next_offset"]
                time.sleep(1)
            
            if self.is_running:  # 如果不是手动终止的
                final_size = self.crawler.downloader.get_size_str()
                self.update_status(f"下载完成！共处理 {total_count} 条帖子，总大小 {final_size}")
                
        except Exception as e:
            error_msg = f"下载过程中发生错误：{str(e)}"
            self.status_var.set(error_msg)
            messagebox.showerror("错误", error_msg)
        finally:
            if not self.is_running:
                self.status_var.set("欢迎再次使用~")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.is_running = False
            
    def update_status(self, text: str):
        """更新状态显示"""
        self.status_var.set(text)
        
    def open_images_folder(self):
        """打开图片保存目录"""
        if not os.path.exists(self.images_path):
            messagebox.showinfo("提示", "下载目录尚未创建，请先下载图片")
            return
            
        # 根据操作系统打开文件夹
        if platform.system() == "Windows":
            os.startfile(self.images_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", self.images_path])
        else:  # Linux
            subprocess.run(["xdg-open", self.images_path])
        
    def open_mys_cos(self):
        """打开米游社cos区"""
        webbrowser.open(self.mys_cos_url)

    def run(self):
        """运行UI"""
        self.root.mainloop()

def main():
    """主函数"""
    ui = MysUI()
    ui.run()

if __name__ == "__main__":
    main()