import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import hashlib
import subprocess
import ctypes
import sys
import psutil
import shutil
import mysql.connector
from mysql.connector import Error
import socket
import requests

class ServerListManager:
    """
    管理用户上传的自定义服务器地址列表的类，数据存储在MySQL数据库的 'custom_servers' 表中。
    """

    def __init__(self, db_config: dict, my_uploader_id: str):
        """
        初始化自定义服务器管理器，并连接到MySQL数据库。

        Args:
            db_config (dict): 包含数据库连接信息的字典。
            my_uploader_id (str): 用于标识当前用户的唯一ID。
        """
        self.db_config = db_config
        self.my_uploader_id = my_uploader_id
        self.connection = None
        self.cursor = None
        self._connect()
        self._create_table_if_not_exists()

        print(f"[ServerListManager] Initialized for database: {db_config.get('database')} on {db_config.get('host')}")
        print(f"[ServerListManager] Your uploader ID: {self.my_uploader_id}")

    def _connect(self):
        """尝试连接到MySQL数据库。"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True)
                print("[ServerListManager] Successfully connected to MySQL database.")
            else:
                print("[ServerListManager] Failed to connect to MySQL database.")
        except Error as e:
            print(f"[ServerListManager] Error connecting to MySQL database: {e}")
            self.connection = None
            self.cursor = None

    def _close(self):
        """关闭数据库连接。"""
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("[ServerListManager] MySQL connection closed.")

    def _execute_query(self, sql: str, params: tuple = None, fetch_results: bool = False) -> list | int | None:
        """
        执行SQL查询或命令。包含自动重连逻辑。
        """
        if not self.connection or not self.connection.is_connected():
            print("[ServerListManager] Database connection is not established or is closed. Attempting to reconnect...")
            self._connect()
            if not self.connection or not self.connection.is_connected():
                print("[ServerListManager] Failed to re-establish database connection. Cannot execute query.")
                return None

        try:
            self.cursor.execute(sql, params)
            if fetch_results:
                return self.cursor.fetchall()
            else:
                self.connection.commit()
                return self.cursor.rowcount
        except Error as e:
            print(f"[ServerListManager] Error executing query: {e}")
            self.connection.rollback()
            return None

    def _create_table_if_not_exists(self):
        """
        检查并创建 'custom_servers' 表，如果它不存在的话。
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS custom_servers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            address VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL, -- 这里用name来存储简介
            uploader VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        print("[ServerListManager] Checking for 'custom_servers' table...")
        result = self._execute_query(create_table_sql)
        if result is not None:
            print("[ServerListManager] 'custom_servers' table checked/created successfully.")
        else:
            print("[ServerListManager] Failed to check/create 'custom_servers' table.")

    def add_server(self, address: str, description: str) -> bool:
        """
        向 'custom_servers' 表添加一行自定义服务器信息。

        Args:
            address (str): 自定义服务器的IP地址。
            description (str): 服务器的简介/名称。

        Returns:
            bool: 如果添加成功则返回True，否则返回False。
        """
        sql = "INSERT INTO custom_servers (address, name, uploader) VALUES (%s, %s, %s)"
        params = (address, description, self.my_uploader_id)
        row_count = self._execute_query(sql, params)
        if row_count == 1:
            print(f"[ServerListManager] Added server to DB: Address='{address}', Description='{description}', Uploader='{self.my_uploader_id}'")
            return True
        else:
            print(f"[ServerListManager] Failed to add server to DB: Address='{address}', Description='{description}'")
            return False
    
    def get_all_servers(self) -> list[dict]:
        """
        从 'custom_servers' 表获取所有服务器条目。
        """
        sql = "SELECT address, name AS description, uploader FROM custom_servers ORDER BY created_at DESC"
        entries = self._execute_query(sql, fetch_results=True)
        return entries if entries is not None else []

    def delete_server_by_address(self, address: str) -> bool:
        """
        从 'custom_servers' 表删除所有匹配指定 'address' 的条目。
        此操作不考虑上传者，只要IP地址匹配就会被删除。

        Args:
            address (str): 要删除的服务器IP地址。

        Returns:
            bool: 如果成功删除一个或多个条目则返回True，否则返回False。
        """
        if not address.strip():
            print("[ServerListManager] Error: Address cannot be empty for deletion.")
            return False

        # SQL语句修改：移除了对 'uploader' 字段的匹配
        sql = "DELETE FROM custom_servers WHERE address = %s"
        # 参数修改：只包含 address
        params = (address,) # 注意这里是 (address,)，元组只有一个元素时需要逗号

        row_count = self._execute_query(sql, params)
        if row_count >= 1:
            print(f"[ServerListManager] Deleted {row_count} entries from DB for Address='{address}'.")
            return True
        else:
            print(f"[ServerListManager] No matching entry found for deletion (address: {address}).")
            return False

class IntranetServerManager:
    def __init__(self, db_config: dict, my_uploader_id: str):
        self.db_config = db_config
        self.my_uploader_id = my_uploader_id
        self.connection = None
        self.cursor = None
        self._connect()
        self._create_table_if_not_exists()

        print(f"Manager initialized for MySQL database: {db_config.get('database')} on {db_config.get('host')}")
        print(f"Your uploader ID: {self.my_uploader_id}")

    def _connect(self):
        """尝试连接到MySQL数据库。"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True) # 使用dictionary=True方便获取字典形式的结果
                print("Successfully connected to MySQL database.")
            else:
                print("Failed to connect to MySQL database.")
        except Error as e:
            print(f"Error connecting to MySQL database: {e}")
            self.connection = None
            self.cursor = None

    def _close(self):
        """关闭数据库连接。"""
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("MySQL connection closed.")

    def _execute_query(self, sql: str, params: tuple = None, fetch_results: bool = False) -> list | int | None:
        """
        执行SQL查询或命令。

        Args:
            sql (str): 要执行的SQL语句。
            params (tuple, optional): SQL语句的参数。Defaults to None.
            fetch_results (bool, optional): 如果为True，则尝试获取查询结果。Defaults to False.

        Returns:
            list | int | None: 如果fetch_results为True，返回查询结果列表；
                               如果为INSERT/UPDATE/DELETE，返回受影响的行数；
                               否则返回None。如果操作失败，返回None。
        """
        if not self.connection or not self.connection.is_connected():
            print("Database connection is not established or is closed. Attempting to reconnect...")
            self._connect()
            if not self.connection or not self.connection.is_connected():
                print("Failed to re-establish database connection. Cannot execute query.")
                return None

        try:
            self.cursor.execute(sql, params)
            if fetch_results:
                return self.cursor.fetchall()
            else:
                self.connection.commit()
                return self.cursor.rowcount # 返回受影响的行数
        except Error as e:
            print(f"Error executing query: {e}")
            self.connection.rollback() # 发生错误时回滚
            return None

    def _create_table_if_not_exists(self):
        """
        检查并创建 'intranet_servers' 表，如果它不存在的话。
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS intranet_servers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            address VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            uploader VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        print("Checking for 'intranet_servers' table...")
        result = self._execute_query(create_table_sql)
        if result is not None:
            print("'intranet_servers' table checked/created successfully.")
        else:
            print("Failed to check/create 'intranet_servers' table.")

    def get_all_entries(self) -> list[dict]:
        """
        从数据库获取所有服务器条目。

        Returns:
            list[dict]: 包含所有服务器条目字典的列表。
        """
        sql = "SELECT address, name, uploader FROM intranet_servers ORDER BY created_at DESC"
        entries = self._execute_query(sql, fetch_results=True)
        if entries is None:
            return []
        return entries

    def add_entry(self, address: str, name: str) -> bool:
        """
        向数据库添加一行内网服务器信息。

        Args:
            address (str): 内网服务器的地址。
            name (str): 内网服务器的名称。

        Returns:
            bool: 如果添加成功则返回True，否则返回False。
        """
        sql = "INSERT INTO intranet_servers (address, name, uploader) VALUES (%s, %s, %s)"
        params = (address, name, self.my_uploader_id)
        row_count = self._execute_query(sql, params)
        if row_count == 1:
            print(f"Added entry to DB: Address='{address}', Name='{name}', Uploader='{self.my_uploader_id}'")
            return True
        else:
            print(f"Failed to add entry to DB: Address='{address}', Name='{name}'")
            return False

    def delete_my_entry(self, address: str) -> bool: # 注意：name 参数已移除
        """
        从数据库销毁（删除）自己上传的一行信息。
        只有当 'address' (IP地址) 和 'uploader' (用户名) 都匹配时才会被删除。

        Args:
            address (str): 要删除的服务器地址。
            # name (str): 此版本不再需要 'name' 参数进行删除匹配。

        Returns:
            bool: 如果成功删除则返回True，否则返回False。
        """
        # SQL语句修改：移除了对 'name' 字段的匹配
        sql = "DELETE FROM intranet_servers WHERE address = %s AND uploader = %s"
        # 参数修改：移除了 'name' 参数
        params = (address, self.my_uploader_id)
        
        row_count = self._execute_query(sql, params)
        if row_count == 1:
            print(f"Deleted entry from DB: Address='{address}', Uploader='{self.my_uploader_id}'")
            return True
        elif row_count == 0:
            print(f"No matching entry found for deletion (address: {address}, uploader: {self.my_uploader_id}).")
            return False
        else:
            # 理论上，如果 address 和 uploader 组合是唯一的，不应该出现 row_count > 1
            # 但为了健壮性，这里保留这个检查
            print(f"Warning: Multiple entries deleted for (address: {address}, uploader: {self.my_uploader_id}). Row count: {row_count}")
            return True # 仍然认为是成功删除了，只是删除了不止一个




class UserManager:
    def __init__(self):
        self.users_file = "users.json"
        self.users = self.load_users()
        
    def load_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_users(self):
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=4)
    
    def register(self, username, password):
        if username in self.users:
            return False
        self.users[username] = {
            'password': self.hash_password(password),
            'karma': 0,
            'servercnt': 0
        }
        self.save_users()
        return True
    
    def login(self, username, password):
        user = self.users.get(username)
        if user and user['password'] == self.hash_password(password):
            return True
        return False
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

class LoginWindow:
    def __init__(self, master, user_manager):
        self.master = master
        self.user_manager = user_manager
        self.setup_ui()
        
    def setup_ui(self):
        self.master.title("AKOS - 用户登录")
        
        self.main_frame = ttk.Frame(self.master, padding="20")
        self.main_frame.pack()
        
        if self.user_manager.users:
            self.show_user_selection()
        else:
            self.show_register_form()
    


    def show_user_selection(self):

        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(self.main_frame, text="选择用户:").grid(row=0, column=0)
        
        self.user_var = tk.StringVar()
        users = list(self.user_manager.users.keys())
        self.user_combobox = ttk.Combobox(
            self.main_frame, 
            textvariable=self.user_var,
            values=users,
            state="readonly"
        )
        self.user_combobox.grid(row=0, column=1)
        self.user_combobox.current(0)
        
        ttk.Label(self.main_frame, text="密码:").grid(row=1, column=0)
        self.password_entry = ttk.Entry(self.main_frame, show="*")
        self.password_entry.grid(row=1, column=1)
        
        ttk.Button(
            self.main_frame, 
            text="登录",
            command=self.handle_login
        ).grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(
            self.main_frame,
            text="注册新用户",
            command=self.show_register_form
        ).grid(row=3, column=0, columnspan=2)
    
    #注册新用户窗口
    def show_register_form(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        ttk.Label(self.main_frame, text="新用户名:").grid(row=0, column=0)
        self.new_user_entry = ttk.Entry(self.main_frame)
        self.new_user_entry.grid(row=0, column=1)
        
        ttk.Label(self.main_frame, text="密码:").grid(row=1, column=0)
        self.new_pass_entry = ttk.Entry(self.main_frame, show="*")
        self.new_pass_entry.grid(row=1, column=1)
        
        ttk.Label(self.main_frame, text="确认密码:").grid(row=2, column=0)
        self.confirm_pass_entry = ttk.Entry(self.main_frame, show="*")
        self.confirm_pass_entry.grid(row=2, column=1)
        
        ttk.Button(
            self.main_frame,
            text="注册",
            command=self.handle_register
        ).grid(row=3, column=0, columnspan=2, pady=10)
        
        if self.user_manager.users:
            ttk.Button(
                self.main_frame,
                text="返回登录",
                command=self.show_user_selection
            ).grid(row=4, column=0, columnspan=2)


    #密码判断
    def handle_login(self):
        username = self.user_var.get()
        password = self.password_entry.get()
        
        if self.user_manager.login(username, password):
            self.master.destroy()
            AKOS(username).run()
        else:
            messagebox.showerror("错误", "用户名或密码错误")
    
    #事件框处理
    def handle_register(self):
        username = self.new_user_entry.get()
        password = self.new_pass_entry.get()
        confirm = self.confirm_pass_entry.get()
        
        if not username or not password:
            messagebox.showerror("错误", "用户名和密码不能为空")
            return
            
        if password != confirm:
            messagebox.showerror("错误", "两次输入的密码不一致")
            return
            
        if self.user_manager.register(username, password):
            messagebox.showinfo("成功", "注册成功，请登录")
            self.show_user_selection()
        else:
            messagebox.showerror("错误", "用户名已存在")

class AKOS:
    def __init__(self, username):
        self.root = tk.Tk()
        self.root.title(f"AKOS v1.0 - 用户: {username}")
        self.username = username
        self.user_manager = UserManager()
        self.setup_ui()
        with open('users.json', 'r', encoding='utf-8') as f:
            self.users_data = json.load(f)
        if self.users_data[self.username]["servercnt"] >= 1:
            MYSQL_DB_CONFIG = {
                "host": "222.79.176.128",
                "port": "53603",
                "user": "public",            
                "password": "123456", 
                "database": "intranet_chat_db" 
            }
            MY_UPLOADER_ID = self.username
            
            ipv4s=socket.gethostbyname_ex(socket.gethostname())[2]

            manager = IntranetServerManager(MYSQL_DB_CONFIG, MY_UPLOADER_ID)
            manager.delete_my_entry(ipv4s[0])

            self.users_data[self.username]["servercnt"] = 0
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump(self.users_data, f, indent=4, ensure_ascii=False)
        
    def rp(self):
        # 直接修改内存中的数据
        self.users_data[self.username]["karma"] += 1
        
        # 更新 Label 显示
        self.karma_var.set(f"{self.username} RP:{self.users_data[self.username]['karma']}")
        
        # 写回 JSON 文件
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(self.users_data, f, indent=4, ensure_ascii=False)

    def rpd(self):
        # 直接修改内存中的数据
        self.users_data[self.username]["karma"] -= 1
        
        # 更新 Label 显示
        self.karma_var.set(f"{self.username} RP:{self.users_data[self.username]['karma']}")
        
        # 写回 JSON 文件
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(self.users_data, f, indent=4, ensure_ascii=False)

    def setup_ui(self):
        # 欢迎
        ttk.Label(self.root, text=f"欢迎使用AKOS, {self.username}! ").pack(pady=10)
        

        # 工具入口区
        self.tool_frame = ttk.LabelFrame(self.root, text="功能工具")
        self.tool_frame.pack(pady=10)
        
        # 添加工具按钮
        tools = [
            ("局域网聊天", self.start_chat),
            ("Python IDE", self.start_python_ide),
            ("C++ IDE", self.start_cpp_ide),
            ("解除极域", self.kill_ey),
            ("玩弄极域", self.play_ey),
            ("解除冰点", self.kill_ice),
            ("PCL2启动", self.start_pcl2)
        ]
        for text, cmd in tools:
            btn = ttk.Button(self.tool_frame, text=text, command=cmd)
            btn.pack(side=tk.LEFT, padx=5)
            
        # 功德区域
        self.other_frame = ttk.LabelFrame(self.root, text="其他操作")
        self.other_frame.pack(pady=10, fill='x')
        # 1.获取RP
        # 1. 获取 karma 值并初始化 ttk.Label
        with open('users.json', 'r', encoding='utf-8') as f:
            self.users_data = json.load(f)
        
        initial_karma = self.users_data[self.username]["karma"]
        self.karma_var = tk.StringVar(value=f"{self.username} RP:{initial_karma}")
        lab = ttk.Label(self.other_frame, textvariable=self.karma_var)
        lab.pack(side=tk.LEFT, padx=5)
        # 2.增加RP按钮
        btn = ttk.Button(self.other_frame, text=f"{self.username} RP++", 
                   command=self.rp)
        btn.pack(side=tk.LEFT, padx=5)
   
        # 3.上传服务器按钮
        btn = ttk.Button(self.other_frame, text = "查看/上传个人服务器(比如mc服务器)", command = self.upload_server)
        btn.pack(side=tk.RIGHT, padx=5)
        # 4.减少RP按钮
        btn = ttk.Button(self.other_frame, text=f"{self.username} RP--?", 
                   command=self.rpd)
        btn.pack(side=tk.RIGHT, padx=5)

        # 退出按钮
        btn = ttk.Button(self.other_frame, text="退出", command=self.root.destroy)
        btn.pack(padx=5, anchor='e', side='right')
            
    # 服务器信息上传
    def get_request_code(self,server_address):
        base_url = "https://uapis.cn"
        endpoint = "/api/v1/game/minecraft/serverstatus"
        url = base_url + endpoint

        # 查询参数，'server' 是必需的
        params = {
            "server": server_address
        }

        try:
            # 发送 GET 请求
            response = requests.get(url, params=params, timeout=10) # 设置超时时间

            # 检查 HTTP 响应状态码
            response.raise_for_status() # 如果状态码不是 200，会抛出 HTTPError 异常

            # 解析 JSON 响应
            data = response.json()
            # 提取 'code' 项
            status_code = data.get("online")
            return status_code
        except:
            tk.messagebox.showerror("错误","获取服务器信息失败，请检查地址是否正确！")
    
    def upload_server(self):
        ans = tk.messagebox.askyesno("选择","你是要上传自己的服务器信息呢？（回答是）还是要查看别人的服务器信息呢？（回答否）")
        if ans == True and self.users_data[self.username]["servercnt"] < 1:
            local = tk.simpledialog.askstring(title="地址",prompt="请输入你的服务器域名/地址，服务器需要公网IP！没有请使用内网穿透")
            try:
                tk.messagebox.showinfo("提示","ping服务器中，请稍等")
                response = self.get_request_code(local)
                result = subprocess.run(['ping', '-n', '1', local], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0 or response:
                    tk.messagebox.showinfo("提示","ping服务器成功！")
                    about = tk.simpledialog.askstring(title="简介",prompt="请输入你的服务器简介")
                    MYSQL_DB_CONFIG = {
                        "host": "222.79.176.128",
                        "port": "53603",
                        "user": "public",            
                        "password": "123456", 
                        "database": "intranet_chat_db" 
                    }
                    MY_UPLOADER_ID = self.username

                    manager = ServerListManager(MYSQL_DB_CONFIG, MY_UPLOADER_ID)
                    try:
                        manager.add_server(local,about)
                        tk.messagebox.showinfo("提示","服务器信息上传成功！请保证服务器开启！如果ping不通会自动删除你的服务器！")
                        self.users_data[self.username]["servercnt"] += 1
                        with open('users.json', 'w', encoding='utf-8') as f:
                            json.dump(self.users_data, f, indent=4, ensure_ascii=False)
                    except:
                        tk.messagebox.showerror("错误","服务器信息上传失败！请检查配置是否正确！")
                else:
                    tk.messagebox.showerror("错误","ping服务器失败，请检查网络连接或检查服务器地址是否正确！")
            except:
                tk.messagebox.showerror("错误","ping服务器失败，请检查网络连接或检查ping是否安装")
        elif ans == False:
            MYSQL_DB_CONFIG = {
                "host": "222.79.176.128",
                "port": "53603",
                "user": "public",            
                "password": "123456", 
                "database": "intranet_chat_db" 
            }
            MY_UPLOADER_ID = self.username
            manager = ServerListManager(MYSQL_DB_CONFIG, MY_UPLOADER_ID)
            all_servers = manager.get_all_servers()
            if all_servers:
                print("自定义服务器列表:")
                tk.messagebox.showinfo("提示","ping所有服务器中，请稍等")
                for server in all_servers:
                    try:
                        local = server['address']
                        response = self.get_request_code(local)
                        result = subprocess.run(['ping', '-n', '1', local], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if result.returncode == 0 or response:
                            print(f"- {'简介: '} | {server['description']} ) | {'上传者: '} | {server['uploader']} ) | {'服务器地址: '} | {server['address'] }")
                        else:
                            resulta = subprocess.run(['ping', '-n', '1', '222.79.176.128'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            if resulta.returncode == 0 and (not result.returncode == 0) and (not response == 200):
                                manager.delete_server_by_address(server['address'])
                                self.users_data[server['uploader']]["servercnt"] -= 1
                                with open('users.json', 'w', encoding='utf-8') as f:
                                    json.dump(self.users_data, f, indent=4, ensure_ascii=False)
                    except:
                        tk.messagebox.showerror("错误","ping服务器失败，请检查网络连接或检查ping是否安装")
            

    # 工具方法实现（示例）
    def start_chat(self):
        ans = tk.messagebox.askyesno("选择","你是要打开一个新的聊天服务器呢？（回答是）还是要加入别人的服务器呢？（回答否）")
        if ans == True:
            if self.users_data[self.username]["servercnt"] >= 1:
                tk.messagebox.showerror("错误","您已经创建了1个服务器，无法再创建记录在册的服务器，将为您打开服务端，请手动创建。")
                pathc="chat/chat.exe"
                subprocess.Popen(pathc)
            else:
                ans = tk.messagebox.askokcancel(title = "提示",message = "我们将获取您的内网IP并上传，其他在同一内网的人将可以看见您的IP并加入您的服务器")
                if ans:
                    local = tk.simpledialog.askstring(title="地址",prompt="请输入您的实际地址比如XXX学校机房和服务器简介（比如某人的服务器）")
                    ipv4s=socket.gethostbyname_ex(socket.gethostname())[2]
                    self.users_data[self.username]["servercnt"] += 1

                    with open('users.json', 'w', encoding='utf-8') as f:
                        json.dump(self.users_data, f, indent=4, ensure_ascii=False)

                    MYSQL_DB_CONFIG = {
                        "host": "222.79.176.128",
                        "port": "53603",
                        "user": "public",            
                        "password": "123456", 
                        "database": "intranet_chat_db" 
                    }
                    MY_UPLOADER_ID = self.username

                    manager = IntranetServerManager(MYSQL_DB_CONFIG, MY_UPLOADER_ID)

                    manager.add_entry(ipv4s[0],local)
                    data1 = ipv4s[0]
                    data2 = "200"
                    data3 = "345"
                    subprocess.Popen(["chat/chat.exe", data1, data2, data3], creationflags=subprocess.CREATE_NEW_CONSOLE)

        else:
            tk.messagebox.showinfo("提示","为了方便复制，我们将在终端内打印所有服务器信息。")
            os.system("cls")
            MYSQL_DB_CONFIG = {
                "host": "222.79.176.128",
                "port": "53603",
                "user": "public",            
                "password": "123456", 
                "database": "intranet_chat_db" 
            }
            MY_UPLOADER_ID = self.username
            manager = IntranetServerManager(MYSQL_DB_CONFIG, MY_UPLOADER_ID)

            subprocess.Popen(["chat/client.exe"])

            all_entries = manager.get_all_entries()
            if all_entries:
                for entry in all_entries:
                    print(f"- 名称： {entry['name']} | 上传者： {entry['uploader']} | 服务器IP： {entry['address']} | 端口： 345")



        
    def start_python_ide(self):
        os.system("start powershell.exe cmd /k 'python'")
        
    def start_cpp_ide(self):
        try:
            with open("dev-c++.txt", "r") as f:
                data = f.readline()
                subprocess.Popen(data)

        except:
            tk.messagebox.showerror("错误",
                                    "未找到Dev-C++请打开dev-c++.txt写入安装目录（或打开安装包安装）。格式：X:/xxx/xxx/xxx/xxx/devcpp.exe")
            subprocess.Popen(["exe/dcsetup.exe"])
        
    def kill_ey(self):
        flag=False
        for process in psutil.process_iter(['name']):
            if process.info['name'] == "StudentMain.exe":
                os.system("taskkill /f /im StudentMain.exe")
                tk.messagebox.showinfo(title="提示", message="极域已被解除")
                flag=True
        if not flag:
            tk.messagebox.showerror("错误","未找到极域进程，请确认极域是否已启动。")
    def play_ey(self):
        flag=False
        for process in psutil.process_iter(['name']):
            if process.info['name'] == "StudentMain.exe":
                pathj="exe/jiyushashou.exe"
                tk.messagebox.showwarning("严重警告","即将打开的软件非AKOS开发，且未经验证是否安全，请谨慎使用！")
                subprocess.Popen(pathj)
                flag=True
                break
        if not flag:
            tk.messagebox.showerror("错误","未找到极域进程，请确认极域是否已启动。")
                        
    def kill_ice(self):
        tk.messagebox.showinfo(title="准备材料", message="您需要一个空U盘")
        tk.messagebox.showwarning("严重警告","您接下来进行的操作可能导致系统崩溃且耗时较长！！为了确保您有亿些专业知识，请回答下列问题（选自CSP-J2024初赛）")
        ans = tk.messagebox.askyesno("问题", "0000，0001，0011，0010，0110，0111，0101，0100是否对应数组 0 至 8 的 4 位二进制格雷码（Gray code）？")
        if ans == True:
            tk.messagebox.showinfo(title="提示", message="回答正确，请插入U盘")
            try:
                subprocess.Popen(["exe/WePE.exe"])
            except:
                bat_file_path = "exe\WePE.bat"
                process = subprocess.Popen(bat_file_path, shell=True)
                # 等待执行完成
                process.wait()
                subprocess.Popen(["exe/WePE.exe"])
            tk.messagebox.showinfo(title="提示", message="请选择右下角安装PE进U盘，选择盘符后确认")
            # copy
            source = "exe/killice.exe"
            target = "E:/"
            try:
                shutil.copy(source, target)
                tk.messagebox.showinfo(title="提示", message="复制成功！请在BIOS使用PE启动。PE系统内打开U盘里的killice.exe，删除冰点还原！")
            except:
                tk.messagebox.showerror(title="错误", message="复制失败，请检查U盘是否正确插入")
            
            
        else:
            tk.messagebox.showinfo(title="提示", message="回答错误，请重新学习")
            


    def start_pcl2(self):
        subprocess.Popen(["PCL2.exe"])
        
    def run(self):
        self.root.mainloop()



# 获取权限


if __name__ == "__main__":   
    if not ctypes.windll.shell32.IsUserAnAdmin():
        if sys.version_info[0] == 3:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        else:#in python2.x
            ctypes.windll.shell32.ShellExecuteW(None, u"runas", unicode(sys.executable), unicode(__file__), None, 1)
        sys.exit() # 调试时去掉
    root = tk.Tk()
    os.startfile('thanks.txt')
    user_manager = UserManager()
    LoginWindow(root, user_manager)
    root.mainloop()
