import time
import random
import threading
import os
import sys
import platform
import subprocess
import zipfile
import requests
import winreg
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    WebDriverException, 
    TimeoutException, 
    NoSuchElementException,
    ElementNotInteractableException,
    ElementClickInterceptedException
)

class EdgeDriverManager:
    """Edge WebDriver 自动管理器"""
    
    def __init__(self):
        self.driver_dir = os.path.join(os.getcwd(), "drivers")
        self.driver_path = os.path.join(self.driver_dir, "msedgedriver.exe")
        self.download_url_template = "https://msedgedriver.microsoft.com/{version}/edgedriver_win64.zip"
        
        # 确保drivers目录存在
        os.makedirs(self.driver_dir, exist_ok=True)
    
    def get_edge_version(self):
        """获取本地Edge浏览器版本"""
        try:
            # 方法1：通过注册表获取
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                  r"Software\Microsoft\Edge\BLBeacon") as key:
                    version = winreg.QueryValueEx(key, "version")[0]
                    return version
            except (FileNotFoundError, OSError):
                pass
            
            # 方法2：通过命令行获取
            try:
                result = subprocess.run(
                    ["powershell", "-Command", 
                     "(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Edge\\BLBeacon').version"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            # 方法3：查找Edge可执行文件版本
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ]
            
            for edge_path in edge_paths:
                if os.path.exists(edge_path):
                    try:
                        result = subprocess.run(
                            [edge_path, "--version"],
                            capture_output=True, text=True, timeout=10
                        )
                        if result.returncode == 0:
                            version_line = result.stdout.strip()
                            version = version_line.split()[-1]
                            return version
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        continue
            
            raise Exception("无法获取Edge浏览器版本")
            
        except Exception as e:
            raise Exception(f"获取Edge版本失败: {str(e)}")
    
    def get_driver_version(self):
        """获取当前msedgedriver.exe版本"""
        if not os.path.exists(self.driver_path):
            return None
        
        try:
            result = subprocess.run(
                [self.driver_path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version_line = result.stdout.strip()
                parts = version_line.split()
                if len(parts) >= 2:
                    return parts[1]
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None
    
    def compare_versions(self, browser_version, driver_version):
        """比较浏览器版本和驱动版本是否匹配"""
        if not browser_version or not driver_version:
            return False
        
        try:
            browser_parts = browser_version.split('.')[:3]
            driver_parts = driver_version.split('.')[:3]
            return browser_parts == driver_parts
        except:
            return False
    
    def download_driver(self, version, progress_callback=None):
        """下载指定版本的msedgedriver"""
        download_url = self.download_url_template.format(version=version)
        zip_path = os.path.join(self.driver_dir, "edgedriver.zip")
        
        try:
            if progress_callback:
                progress_callback(f"正在下载 msedgedriver {version}...")
            
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            progress_callback(f"下载进度: {progress:.1f}%")
            
            if progress_callback:
                progress_callback("正在解压文件...")
            
            # 解压文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.endswith('msedgedriver.exe'):
                        with zip_ref.open(file_info) as source:
                            with open(self.driver_path, 'wb') as target:
                                target.write(source.read())
                        break
            
            # 删除临时zip文件
            os.remove(zip_path)
            
            if progress_callback:
                progress_callback(f"msedgedriver {version} 下载完成!")
            
            return True
            
        except requests.RequestException as e:
            raise Exception(f"下载失败: {str(e)}")
        except zipfile.BadZipFile:
            raise Exception("下载的文件损坏")
        except Exception as e:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            raise Exception(f"下载或解压失败: {str(e)}")
    
    def check_and_update_driver(self, progress_callback=None):
        """检查并更新WebDriver"""
        try:
            if progress_callback:
                progress_callback("正在检测Edge浏览器版本...")
            
            browser_version = self.get_edge_version()
            
            if progress_callback:
                progress_callback(f"检测到Edge版本: {browser_version}")
            
            driver_version = self.get_driver_version()
            
            if driver_version:
                if progress_callback:
                    progress_callback(f"当前驱动版本: {driver_version}")
                
                if self.compare_versions(browser_version, driver_version):
                    if progress_callback:
                        progress_callback("版本匹配，无需更新")
                    return self.driver_path
                else:
                    if progress_callback:
                        progress_callback("版本不匹配，需要更新驱动")
            else:
                if progress_callback:
                    progress_callback("未找到驱动文件，需要下载")
            
            self.download_driver(browser_version, progress_callback)
            return self.driver_path
            
        except Exception as e:
            raise Exception(f"WebDriver检查更新失败: {str(e)}")

class AutoClicker:
    def __init__(self, driver_path=None):
        """
        初始化自动点击器
        Args:
            driver_path: WebDriver可执行文件路径（可选，将自动管理）
        """
        self.driver_manager = EdgeDriverManager()
        self.driver = None
        self.paused = False
        self.stop_flag = False
        self.pause_lock = threading.Condition()
        self.is_running = False
        
        # 如果提供了driver_path但文件不存在，不抛出错误，使用自动管理
        if driver_path and os.path.isfile(driver_path):
            self.custom_driver_path = driver_path
        else:
            self.custom_driver_path = None
        
    def get_driver_path(self, update_status=None):
        """获取WebDriver路径，优先使用自定义路径"""
        if self.custom_driver_path:
            return self.custom_driver_path
        else:
            return self.driver_manager.check_and_update_driver(update_status)

    def start(self, username, password, update_status, custom_interval, txt_book_id, interval):
        """启动自动化流程"""
        try:
            self.is_running = True
            self.stop_flag = False
            
            # 获取WebDriver路径
            update_status("正在检查WebDriver...")
            driver_path = self.get_driver_path(update_status)
            
            update_status("正在启动浏览器...")
            
            # 配置Edge选项
            edge_options = EdgeOptions()
            edge_options.add_argument("--disable-blink-features=AutomationControlled")
            edge_options.add_argument("--disable-dev-shm-usage")
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            edge_options.add_experimental_option('useAutomationExtension', False)
            
            # 创建WebDriver实例
            service = EdgeService(driver_path)
            self.driver = webdriver.Edge(service=service, options=edge_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            update_status("浏览器启动成功，开始登录...")
            
            # 执行登录和操作
            self.login(username, password, update_status)
            self.navigate_and_click(update_status, custom_interval, txt_book_id, interval)
            
        except WebDriverException as e:
            error_msg = f"WebDriver错误: {str(e)}"
            print(error_msg)
            update_status(error_msg)
            messagebox.showerror("WebDriver错误", f"浏览器启动失败:\n{str(e)}")
            
        except Exception as e:
            error_msg = f"程序错误: {str(e)}"
            print(error_msg)
            update_status(error_msg)
            messagebox.showerror("程序错误", str(e))
            
        finally:
            self.is_running = False
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

    def login(self, username, password, update_status):
        """执行登录操作 - 简化版，只输入用户名密码"""
        try:
            update_status("正在访问登录页面...")
            self.driver.get("https://ucloud.unipus.cn/sso/index.html?service=https%3A%2F%2Fucloud.unipus.cn%2Fhome")
            
            # 等待页面加载完成
            update_status("等待页面加载...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            
            time.sleep(2)  # 额外等待确保页面完全加载
            
            # 输入用户名
            update_status("输入用户名...")
            username_field = self.driver.find_element(By.ID, "username")
            username_field.clear()
            time.sleep(0.5)
            username_field.send_keys(username)
            
            time.sleep(1)
            
            # 输入密码
            update_status("输入密码...")
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            time.sleep(0.5)
            password_field.send_keys(password)
            
            time.sleep(1)
            
            # 弹窗提醒用户手动登录
            update_status("等待用户手动登录...")
            messagebox.showinfo(
                "手动登录提醒", 
                "账号密码已自动填写完成！\n\n请您手动：\n1. 勾选用户协议\n2. 点击登录按钮\n\n登录成功后程序将自动继续操作"
            )
            
            # 等待用户登录成功
            self.wait_for_login_success(update_status)
            
            update_status("登录成功，准备进入课程...")
            
        except TimeoutException:
            raise Exception("登录页面加载超时，请检查网络连接")
        except NoSuchElementException as e:
            raise Exception(f"页面元素未找到: {str(e)}")

    def wait_for_login_success(self, update_status):
        """等待用户登录成功"""
        max_wait_time = 300  # 最多等待5分钟
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            if self.stop_flag:
                raise Exception("用户取消操作")
            
            try:
                # 检查是否已经跳转到登录成功后的页面
                current_url = self.driver.current_url
                
                # 如果URL包含home或者不包含sso，说明登录成功
                if "home" in current_url or "sso" not in current_url:
                    time.sleep(2)  # 额外等待确保页面稳定
                    return
                
                # 检查是否有登录错误信息
                try:
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .alert, .warning")
                    for element in error_elements:
                        if element.is_displayed() and element.text.strip():
                            error_text = element.text.strip()
                            if any(keyword in error_text for keyword in ['错误', '失败', '用户名', '密码', 'error', 'Error']):
                                messagebox.showerror("登录失败", f"检测到登录错误信息：{error_text}\n请检查用户名密码后重新尝试")
                                raise Exception("登录失败")
                except:
                    pass
                
                time.sleep(2)
                update_status(f"等待登录完成... ({int(max_wait_time - (time.time() - start_time))}秒)")
                
            except Exception as e:
                if "登录失败" in str(e):
                    raise e
                # 其他异常继续等待
                time.sleep(2)
        
        raise Exception("等待登录超时，请检查是否登录成功")

    def navigate_and_click(self, update_status, custom_interval, txt_book_id, interval):
        """导航到课程页面并执行点击操作"""
        try:
            update_status("正在进入课程页面...")
            course_url = f"https://ucloud.unipus.cn/app/cmgt/resource-detail/{txt_book_id}"
            self.driver.get(course_url)
            
            # 等待页面加载
            time.sleep(5)
            
            # 页面滚动
            update_status("页面滚动中...")
            self.driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(3)
            
            # 点击各种按钮（增加延时）
            update_status("点击课程按钮...")
            self.click_button_safe("button.ant-btn.ant-btn-default.courses-info_buttonLayer1__Mtel4 span")
            time.sleep(3)
            
            update_status("点击知识点按钮...")
            self.click_button_safe("div.know-box span.iKnow")
            time.sleep(3)
            
            update_status("点击确认按钮...")
            self.click_button_safe("button.ant-btn.ant-btn-primary span")
            time.sleep(3)
            
            # 处理可能的弹窗
            self.handle_popup_dialogs(update_status)
            time.sleep(2)
            
            # 获取所有菜单项
            update_status("获取课程菜单...")
            buttons = WebDriverWait(self.driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.pc-slider-menu-micro.pc-menu-default"))
            )
            
            update_status(f"找到 {len(buttons)} 个课程项目，从第 {custom_interval + 1} 个开始")
            time.sleep(2)
            
            # 遍历并点击按钮
            for index, button in enumerate(buttons[custom_interval:], start=custom_interval):
                if self.stop_flag:
                    update_status("操作已停止")
                    break
                
                try:
                    # 滚动到元素位置
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(2)
                    
                    # 点击菜单项
                    button.click()
                    current_task = button.text.strip() or f"课程项目 {index + 1}"
                    update_status(f"正在学习: {current_task}")
                    
                    time.sleep(3)  # 等待页面响应
                    
                    # 点击确认按钮（继续学习按钮）
                    update_status("点击继续学习按钮...")
                    time.sleep(2)  # 在点击继续学习按钮前慢一点
                    self.click_button_safe("button.ant-btn.ant-btn-primary span")
                    
                    time.sleep(2)  # 点击后也等待一下
                    
                    # 处理可能的弹窗
                    self.handle_popup_dialogs(update_status)
                    
                    # 等待随机时间
                    random_interval = max(30, interval + random.randint(-20, 20))
                    self.wait_with_update(random_interval, update_status, current_task)
                    
                    # 额外等待时间
                    time.sleep(30)
                    
                except Exception as e:
                    error_msg = f"处理第 {index + 1} 个项目时出错: {str(e)}"
                    print(error_msg)
                    update_status(error_msg)
                    time.sleep(5)  # 出错时也等待一下再继续
                    continue
            
            if not self.stop_flag:
                update_status("所有课程项目处理完成！")
            
        except TimeoutException:
            raise Exception("课程页面加载超时")
        except Exception as e:
            raise Exception(f"导航过程出错: {str(e)}")

    def handle_popup_dialogs(self, update_status):
        """处理弹窗对话框"""
        popup_button_texts = ['我知道了', '知道了', '确定', '确认', 'OK', '好的', '关闭']
        
        try:
            for text in popup_button_texts:
                try:
                    buttons = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            try:
                                button.click()
                                update_status(f"处理弹窗: 点击了'{text}'按钮")
                                time.sleep(2)
                                return
                            except:
                                try:
                                    self.driver.execute_script("arguments[0].click();", button)
                                    update_status(f"处理弹窗: 使用JS点击了'{text}'按钮")
                                    time.sleep(2)
                                    return
                                except:
                                    continue
                except:
                    continue
        except:
            pass

    def click_button_safe(self, selector, wait_time=30):
        """安全点击按钮（带异常处理和重试）"""
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                button = WebDriverWait(self.driver, wait_time).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(1)
                button.click()
                time.sleep(2)
                return
            except TimeoutException:
                print(f"警告: 按钮未找到或不可点击 - {selector} (重试 {retry + 1}/{max_retries})")
                if retry == max_retries - 1:
                    print(f"最终失败: {selector}")
            except ElementNotInteractableException:
                print(f"警告: 按钮不可交互 - {selector} (重试 {retry + 1}/{max_retries})")
                if retry < max_retries - 1:
                    time.sleep(3)
            except Exception as e:
                print(f"点击按钮时出错 - {selector}: {str(e)} (重试 {retry + 1}/{max_retries})")
                if retry < max_retries - 1:
                    time.sleep(3)

    def wait_with_update(self, interval, update_status, current_task):
        """带状态更新的等待功能"""
        for i in range(interval, 0, -1):
            with self.pause_lock:
                while self.paused and not self.stop_flag:
                    self.pause_lock.wait()
                    
            if self.stop_flag:
                return
                
            update_status(f"{current_task}", i)
            time.sleep(1)

    def pause(self):
        """暂停操作"""
        self.paused = True

    def resume(self):
        """恢复操作"""
        with self.pause_lock:
            self.paused = False
            self.pause_lock.notify()

    def stop(self):
        """停止操作"""
        self.stop_flag = True
        self.resume()

# 全局变量
clicker = None
script_thread = None

def start_script():
    """启动脚本"""
    try:
        # 验证输入
        username = txt_username.get().strip()
        password = txt_password.get().strip()
        book_id = txt_book_id.get().strip()
        
        if not username or not password or not book_id:
            messagebox.showerror("输入错误", "请填写所有必需字段！")
            return
        
        try:
            custom_interval = int(txt_custom_interval.get() or "0")
            interval = int(txt_interval.get() or "60")
        except ValueError:
            messagebox.showerror("输入错误", "转跳和时间间隔必须是数字！")
            return
        
        if custom_interval < 0 or interval < 30:
            messagebox.showerror("输入错误", "转跳不能小于0，时间间隔不能小于30秒！")
            return
        
        # 检查是否已有线程在运行
        global script_thread, clicker
        if script_thread and script_thread.is_alive():
            messagebox.showwarning("警告", "程序正在运行中！")
            return
        
        # 创建AutoClicker实例
        clicker = AutoClicker()
        
        # 启动线程
        update_status("正在启动...")
        script_thread = threading.Thread(
            target=clicker.start, 
            args=(username, password, update_status, custom_interval, book_id, interval),
            daemon=True
        )
        script_thread.start()
        
        # 更新按钮状态
        btn_start.config(state="disabled")
        btn_stop.config(state="normal")
        btn_pause.config(state="normal")
        
    except Exception as e:
        messagebox.showerror("启动错误", f"启动失败: {str(e)}")

def pause_script():
    """暂停脚本"""
    if clicker and clicker.is_running:
        clicker.pause()
        update_status("已暂停")
        btn_pause.config(state="disabled")
        btn_resume.config(state="normal")

def resume_script():
    """恢复脚本"""
    if clicker:
        clicker.resume()
        update_status("已恢复")
        btn_pause.config(state="normal")
        btn_resume.config(state="disabled")

def stop_script():
    """停止脚本"""
    global script_thread
    if clicker:
        clicker.stop()
    
    # 重置按钮状态
    btn_start.config(state="normal")
    btn_stop.config(state="disabled")
    btn_pause.config(state="disabled")
    btn_resume.config(state="disabled")
    
    update_status("操作已停止")

def update_status(current_task, countdown=0):
    """更新状态显示"""
    try:
        if countdown > 0:
            lbl_status.config(text=f"当前操作: {current_task}")
            lbl_countdown.config(text=f"下一个操作倒数: {countdown} 秒")
        else:
            lbl_status.config(text=f"当前操作: {current_task}")
            lbl_countdown.config(text="下一个操作倒数: 无")
    except:
        pass

def manual_check_driver():
    """手动检查驱动更新"""
    def check_in_thread():
        try:
            manager = EdgeDriverManager()
            
            def progress_update(msg):
                check_window.after(0, lambda: progress_label.config(text=msg))
            
            driver_path = manager.check_and_update_driver(progress_update)
            
            check_window.after(0, lambda: (
                progress_label.config(text="检查完成！"),
                messagebox.showinfo("检查完成", f"WebDriver已准备就绪:\n{driver_path}"),
                check_window.destroy()
            ))
            
        except Exception as e:
            check_window.after(0, lambda: (
                progress_label.config(text="检查失败"),
                messagebox.showerror("检查失败", str(e)),
                check_window.destroy()
            ))
    
    # 创建进度窗口
    check_window = tk.Toplevel()
    check_window.title("检查WebDriver")
    check_window.geometry("400x100")
    check_window.attributes("-topmost", True)
    check_window.resizable(False, False)
    
    progress_label = tk.Label(check_window, text="正在检查...", wraplength=350)
    progress_label.pack(pady=20)
    
    # 启动检查线程
    check_thread = threading.Thread(target=check_in_thread, daemon=True)
    check_thread.start()

def create_ui():
    """创建用户界面"""
    window = tk.Tk()
    window.title("Unipus自动刷课工具 v2.1.0 (手动登录版)")
    window.geometry("400x650")  # 增加窗口高度
    window.attributes("-topmost", True)
    window.resizable(False, False)
    
    # 设置全局变量
    global txt_username, txt_password, txt_book_id, txt_custom_interval, txt_interval
    global lbl_status, lbl_countdown
    global btn_start, btn_stop, btn_pause, btn_resume
    
    # WebDriver状态显示
    frame_driver_info = tk.Frame(window, relief=tk.RAISED, bd=1)
    frame_driver_info.pack(fill=tk.X, padx=10, pady=5)
    
    lbl_driver_title = tk.Label(frame_driver_info, text="🤖 智能WebDriver管理", font=("Arial", 10, "bold"))
    lbl_driver_title.pack(pady=2)
    
    lbl_driver_info = tk.Label(frame_driver_info, text="✅ 自动检测Edge版本\n✅ 自动下载匹配驱动\n✅ 无需手动配置", 
                              fg="blue", font=("Arial", 8))
    lbl_driver_info.pack(pady=2)
    
    btn_check_driver = tk.Button(frame_driver_info, text="手动检查更新", command=manual_check_driver, width=15)
    btn_check_driver.pack(pady=5)
    
    # 账号密码
    lbl_username = tk.Label(window, text="手机号:")
    lbl_username.pack(anchor="w", padx=10, pady=(10, 0))
    
    txt_username = tk.Entry(window, width=45)
    txt_username.pack(padx=10, pady=2)
    
    lbl_password = tk.Label(window, text="密码:")
    lbl_password.pack(anchor="w", padx=10, pady=(5, 0))
    
    txt_password = tk.Entry(window, width=45, show="*")
    txt_password.pack(padx=10, pady=2)
    
    # 课本ID
    lbl_book_id = tk.Label(window, text="课本ID:")
    lbl_book_id.pack(anchor="w", padx=10, pady=(5, 0))
    
    txt_book_id = tk.Entry(window, width=45)
    txt_book_id.pack(padx=10, pady=2)
    
    # 转跳设置
    lbl_custom_interval = tk.Label(window, text="从第几个开始 (默认0):")
    lbl_custom_interval.pack(anchor="w", padx=10, pady=(5, 0))
    
    txt_custom_interval = tk.Entry(window, width=45)
    txt_custom_interval.insert(0, "0")
    txt_custom_interval.pack(padx=10, pady=2)
    
    # 时间间隔
    lbl_interval = tk.Label(window, text="时间间隔 (秒，最小30):")
    lbl_interval.pack(anchor="w", padx=10, pady=(5, 0))
    
    txt_interval = tk.Entry(window, width=45)
    txt_interval.insert(0, "60")
    txt_interval.pack(padx=10, pady=2)
    
    # 控制按钮
    frame_buttons = tk.Frame(window)
    frame_buttons.pack(pady=15)
    
    btn_start = tk.Button(frame_buttons, text="开始", command=start_script, width=10, bg="#4CAF50", fg="white")
    btn_start.pack(side=tk.LEFT, padx=5)
    
    btn_pause = tk.Button(frame_buttons, text="暂停", command=pause_script, width=10, state="disabled")
    btn_pause.pack(side=tk.LEFT, padx=5)
    
    btn_resume = tk.Button(frame_buttons, text="继续", command=resume_script, width=10, state="disabled")
    btn_resume.pack(side=tk.LEFT, padx=5)
    
    btn_stop = tk.Button(frame_buttons, text="停止", command=stop_script, width=10, bg="#f44336", fg="white", state="disabled")
    btn_stop.pack(side=tk.LEFT, padx=5)
    
    # 状态显示
    lbl_status = tk.Label(window, text="当前操作: 无", fg="blue", wraplength=350)
    lbl_status.pack(pady=5)
    
    lbl_countdown = tk.Label(window, text="下一个操作倒数: 无", fg="green")
    lbl_countdown.pack(pady=2)
    
    # 使用说明 - 使用Text控件
    usage_frame = tk.Frame(window)
    usage_frame.pack(padx=10, pady=10, fill=tk.BOTH)
    
    txt_usage = tk.Text(usage_frame, 
                       height=6,  # 固定高度为6行
                       width=45, 
                       font=("Arial", 8),
                       fg="gray",
                       bg=window.cget('bg'),  # 与窗口背景色一致
                       relief=tk.FLAT,
                       wrap=tk.WORD,
                       state=tk.DISABLED,  # 只读
                       cursor="arrow")  # 设置鼠标指针样式
    
    usage_text = ("📝 使用说明:\n"
                  "1. 填写登录信息和课本ID\n"
                  "2. 点击开始，程序会自动填写账号密码\n"
                  "3. 在弹出提醒后，请手动勾选协议并点击登录\n"
                  "4. 登录成功后程序自动继续刷课\n"
                  "💡 程序已优化速度，不会过快操作")
    
    txt_usage.config(state=tk.NORMAL)
    txt_usage.insert(tk.END, usage_text)
    txt_usage.config(state=tk.DISABLED)
    txt_usage.pack()
    
    # 窗口关闭事件
    def on_closing():
        if clicker and clicker.is_running:
            if messagebox.askokcancel("退出", "程序正在运行，确定要退出吗？"):
                stop_script()
                window.destroy()
        else:
            window.destroy()
    
    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.mainloop()

if __name__ == "__main__":
    try:
        create_ui()
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        messagebox.showerror("启动错误", f"程序启动失败:\n{str(e)}")
