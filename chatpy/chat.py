import socket
import re
import tabulate
import requests
import cmd
import datetime
import threading
import sys
import json

CONFIG_PATH = "config.json"

try:
    with open(CONFIG_PATH, "r+") as f:
        dic_tmp = json.load(f)
        ban_ip, ban_words, ban_length = dic_tmp['ban']['ip'], dic_tmp['ban']['words'], dic_tmp['ban']['length']
        status_enter_after_promis_tmp = dic_tmp['ENTER_AFTER_PROMISE']
        status_show_enter_message_tmp = dic_tmp['SHOW_ENTER_MESSAGE']
        if type(ban_ip) == type(list()) and type(ban_words) == type(list()) and type(ban_length) == type(int()) and type(status_enter_after_promis_tmp) == type(bool()) and type(status_show_enter_message_tmp) == type(bool()):
            pass
        
        else:
            raise

        for v in ban_ip:
            if (type(v) != type(str())):
                raise
        
        for v in ban_words:
            if (type(v) != type(str())):
                raise
        
except:
    with open(CONFIG_PATH, "w+") as f:
        json.dump({
            "ban" : {
                "words" : [],
                "ip" : [],
                "length": 2147483647
            },
            "ENTER_AFTER_PROMISE" : False,
            "SHOW_ENTER_MESSAGE" : False
        }, f)

if len(sys.argv) == 4:
    ip = sys.argv[1]
    account_numbers = sys.argv[2]
    portin = sys.argv[3]
    try:
        account_numbers = int(account_numbers)
        portin = int(portin)
    except:
        print("[Error] 参数输入不正确")
        exit()

else:
    nums = input()
    ip = nums[0]
    account_numbers = eval(nums[1])
    portin = eval(nums[2])

s = socket.socket()
s.bind((ip, portin))
s.listen(account_numbers)
s.setblocking(0)

VERSION = "v1.1.2"
s.setblocking(0)
NEWEST_VERSION = "UNKNOWN"

try:
    NEWEST_VERSION = requests.get("https://bopid.cn/chat/newest_version_chat.html").content.decode()
except:
    NEWEST_VERSION = "UNKNOWN"

def time_str() -> str:
    return str(datetime.datetime.now())

with open("./log.txt", "w+") as file:
    file.write(f"[{time_str()}] TouchFish(Server) started successfully, {ip}:{portin}.\n")

"""
conn:       链接操作口          [socket.socket()]
address:    IP                 [(str, int)]
username:   用户名、IP对应      {str : str}
requestion: 申请加入队列        [(socket.socket(), (str, int)) or None]
"""
conn = []
address = []
username = dict()
if_online = dict()
requestion = []
msg_counts = dict()
dic_config_file = json.load(open(CONFIG_PATH, "r+"))
ban_ip_lst = dic_config_file["ban"]["ip"]
ban_words_lst = dic_config_file["ban"]["words"]
ban_length = dic_config_file["ban"]["length"]
ENTER_AFTER_PROMISE = dic_config_file["ENTER_AFTER_PROMISE"]

ENTER_HINT = ""
with open("hint.txt", "a+", encoding="utf-8") as file:
    file.seek(0)
    ENTER_HINT = file.read()
if not ENTER_HINT.split('\n'):
    ENTER_HINT = ""
if ENTER_HINT and ('\n' not in ENTER_HINT):
    ENTER_HINT += '\n'

print("您当前的进入提示是（注意使用的是 utf-8）：" + ENTER_HINT)
SHOW_ENTER_MESSAGE = dic_config_file["SHOW_ENTER_MESSAGE"]
EXIT_FLG = False 
flush_txt = ""

def send_all(msg : str):
    global conn
    for j in range(len(conn)):
        try:
            conn[j].send(bytes(msg, encoding="utf-8"))
            if_online[address[j][0]] = True
        except:
            if_online[address[j][0]] = False

def add_accounts():
    global flush_txt
    while True:
        if EXIT_FLG:
            return
        if (len(conn) > account_numbers):
            print("注意：连接数已满")
            sys.stdout.flush()
            break
        conntmp = None
        addresstmp = None
        try:
            conntmp, addresstmp = s.accept()
        except:
            continue
        
        try:
            if ENTER_HINT:
                conntmp.send(bytes("[房主提示] " + ENTER_HINT, encoding="utf-8"))
        except:
            pass

        if addresstmp[0] in ban_ip_lst:
            continue
        
        if ENTER_AFTER_PROMISE:
            try:
                conntmp.send(bytes("[系统提示] 本聊天室需要房主确认后加入，请等待房主同意。\n", encoding="utf-8"))
            except:
                pass
            flush_txt += f"[{time_str()}] <{len(requestion)}> User {addresstmp} request to enter the chatting room.\n"
            print(f"\n<{len(requestion)}> 用户 {addresstmp} 申请加入聊天室，请处理。\n{ip}:{portin}> ", end="")
            sys.stdout.flush()
            requestion.append((conntmp, addresstmp))
            continue
        
        if SHOW_ENTER_MESSAGE:
            print(f"\n用户 {addresstmp} 加入聊天室！\n{ip}:{portin}> ", end="")
            sys.stdout.flush()


        if_online[addresstmp[0]] = True
        msg_counts[addresstmp[0]] = 0 
        flush_txt += f"[{time_str()}] User {addresstmp} connected to server.\n"
        
        conntmp.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)

        # 对于 Linux 系统，请将下面的代码解除注释，注释下面的 3 行代码注释，直接运行。
        """
        conntmp.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 180 * 60)
        conntmp.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30)
        """
        
        conntmp.ioctl(socket.SIO_KEEPALIVE_VALS, (
            1, 180 * 1000, 30 * 1000
        ))
        conntmp.setblocking(0)
        conn.append(conntmp)
        address.append(addresstmp)
        username[addresstmp[0]] = "UNKNOWN"

def receive_msg():
    global flush_txt
    while True:
        if EXIT_FLG:
            return
        for i in range(len(conn)):
            data = None
            try:
                data = conn[i].recv(1024).decode('utf-8')
            except:
                continue
            if address[i][0] in ban_ip_lst:
                continue
            if not data:
                continue
            msg_counts[address[i][0]] += 1
            if len(data) > ban_length:
                continue
            flg = False
            for v in ban_words_lst:
                if v in data:
                    flg = True
                    continue
            if flg:
                continue
            username_tmp = data.split(':')[0]
            username[address[i][0]] = username_tmp
            flush_txt += f"[{time_str()}] User {address[i]} send a msg: {data}"
            for j in range(len(conn)):
                try:
                    conn[j].send(bytes(data, encoding="utf-8"))
                    if_online[address[j][0]] = True
                except:
                    if_online[address[j][0]] = False
                    continue
 
class Server(cmd.Cmd):
    prompt = f"{ip}:{portin}> "
    intro = f"""欢迎来到 TouchFish！当前版本 {VERSION}，最新版本 {NEWEST_VERSION}
如果想知道有什么命令，请输入 help
具体的使用指南，参见 help <你想用的命令>。详细地，见 wiki，https://github.com/2044-space-elevator/TouchFish/wiki/How-to-use-chat.exe
注意：消息无法实时更新，需要输入 flush 命令将缓冲区输出到 ./log.txt。
永久配置文件位于目录下的 ./config.json"""
    def __init__(self):
        cmd.Cmd.__init__(self)

    def do_enable(self, arg : list):
        """
        使用方法（~ 表示 enable)：
            ~ ip <*ip1> <*ip2> ... <*ipk>   解禁这 k 个 ip
            ~ words <*w1> <*w2> ... <*wk>   删除这 k 个屏蔽词
            在 enable 命令的后面直接加 forever，可以使得本设置保存到配置文件。下一次启动本目录的 server 时能使用。
        """
        global ban_ip_lst
        global flush_txt
        global ban_words_lst
        global ban_length
        global dic_config_file

        arg = arg.split(' ')
        if len(arg) < 2:
            print("[Error] 参数错误")
            return
        SAVE_CONFIG = False
        if arg[0] == 'forever':
            SAVE_CONFIG = True
            arg = arg[1:]
        
        att1 = ["ip", "words"]
        if arg[0] not in att1:
            print("[Error] 参数错误")
            return
        
        if arg[0] == 'ip':
            arg = arg[1:]
            for ip in arg:
                if SAVE_CONFIG:
                    try:
                        dic_config_file["ban"]["ip"].remove(ip)
                    except:
                        pass
                try:
                    ban_ip_lst.remove(ip)
                    send_all(f"[系统提示] 房主解除封禁了 IP {ip}，用户名 {username[ip]}。\n")
                except:
                    pass
            flush_txt += f"[{time_str()}] You unbanned ip {','.join(arg)}.\n"
        
        if arg[0] == 'words':
            arg = arg[1:]
            for word in arg:
                if SAVE_CONFIG:
                    try:
                        dic_config_file["ban"]["words"].remove(word)
                    except:
                        pass
                try:
                    ban_words_lst.remove(word)
                except:
                    pass
            flush_txt += f"[{time_str()}]You unbanned words {','.join(arg)}.\n"
        
    def do_ban(self, arg : list):
        """
        使用方法（~ 表示 ban)：
            ~ ip <*ip1> <*ip2> ... <*ipk>   封禁这 k 个 ip
            ~ words <*w1> <*w2> ... <*wk>   添加这 k 个屏蔽词
            ~ length <*len>                 拒绝分发所有长度大于 len 的信息
            在 ban 命令的后面直接加 forever，可以使得本设置保存到配置文件。下一次启动本目录的 server 时能使用。
        """
        global ban_ip_lst
        global flush_txt
        global ban_words_lst
        global ban_length
        global dic_config_file

        arg = arg.split(' ')
        if len(arg) < 2:
            print("[Error] 参数错误")
            return
        SAVE_CONFIG = False
        if arg[0] == 'forever':
            SAVE_CONFIG = True
            arg = arg[1:]
        
        att1 = ["ip", "words", "length"]
        if arg[0] not in att1:
            print("[Error] 参数错误")
            return
        
        if arg[0] == 'ip':
            arg = arg[1:]
            for ip in arg:
                if SAVE_CONFIG:
                    dic_config_file["ban"]["ip"].append(ip)
                ban_ip_lst.append(ip)
                send_all(f"[系统提示] 房主封禁了用户 {ip}, 用户名：{username[ip]}\n")
            flush_txt += f"[{time_str()}] You banned ip {','.join(arg)}.\n"
        
        if arg[0] == 'words':
            arg = arg[1:]
            for word in arg:
                if SAVE_CONFIG:
                    dic_config_file["ban"]["words"].append(word)
                ban_words_lst.append(word)
            flush_txt += f"[{time_str()}] You banned words {','.join(arg)}.\n"
        
        if arg[0] == "length":
            try:
                arg[1] = int(arg[1])
            except:
                print("[Error] 参数错误")
                return
            send_all(f"[系统提示] 房主设置了发送信息的长度最高为 {arg[1]}。\n")
            if SAVE_CONFIG:
                dic_config_file["ban"]["length"] = arg[1]
            ban_length = arg[1]
            flush_txt += f"[{time_str()}] You limited message length: {ban_length}\n"

        if SAVE_CONFIG:
            with open(CONFIG_PATH, "w+") as f:
                json.dump(dic_config_file, f)

    def do_set(self, arg):
        """
        使用方法（~ 表示 set)：
            ~ EAP on/off 开启/关闭准许后进入
            ~ SEM on/off 开启/关闭进入后提示
            你可以在命令后面加上 "forever"，表示将设置保存到配置文件。下一次启动本目录的 server 时能使用。
        """
        global flush_txt
        arg = arg.split(' ')
        if len(arg) != 2 and len(arg) != 3:
            print("[Error] 参数错误")
            return
        att1 = ["EAP", "SEM"]
        att2 = ["on", "off"]
        att3 = "forever"
        if (arg[0] not in att1) or (arg[1] not in att2):
            print("[Error] 参数错误")
            return
        if len(arg) == 3 and arg[2] != att3:
            print("[Error] 参数错误")
            return
        global ENTER_AFTER_PROMISE
        global SHOW_ENTER_MESSAGE
        global dic_config_file
        if arg[0] == "EAP":
            if arg[1] == "on":
                ENTER_AFTER_PROMISE = True
            else:
                ENTER_AFTER_PROMISE = False
        
        if arg[0] == "SEM":
            if arg[1] == "off":
                SHOW_ENTER_MESSAGE = False
            else:
                SHOW_ENTER_MESSAGE = True
        flush_txt += f'You set {arg[0]} as {arg[1]}'
        if len(arg) == 3:
            flush_txt += f" and save it in config."
            dic_config_file["ENTER_AFTER_PROMISE"] = ENTER_AFTER_PROMISE
            dic_config_file["SHOW_ENTER_MESSAGE"] = SHOW_ENTER_MESSAGE
            with open(CONFIG_PATH, "w+") as file:
                json.dump(dic_config_file, file)
        flush_txt += '\n'

    def print_user(self, userlist : list[str]):
        header = ["IP", "USERNAME", "IS_ONLINE", "IS_BANNED", "SEND_TIMES"]
        data_body = []
        for ip in userlist:
            data_body.append([ip, username[ip], if_online[ip], ip in ban_ip_lst, msg_counts[ip]])
        print(tabulate.tabulate(data_body, headers=header))

    def reject(self, rid : int):
        global flush_txt
        try:
            flush_txt += f"[{time_str()}] <{rid}> User {requestion[rid][1]} was rejected to enter in the chatting room.\n"
            print(f"您拒绝第 {rid} 号请求（用户 {requestion[rid][1]}）。")
            requestion[rid][0].send(bytes("[系统提示] 您被拒绝加入聊天室\n", encoding="utf-8"))
            requestion[rid] = None
        except:
            print(f"[Error] 第 {rid} 次提示信息发送失败")
    
    def accept(self, rid : int):
        global flush_txt
        if not requestion[rid]:
            print(f"[Error] 第 {rid} 号进入请求已处理")
            return
        try:
            if_online[requestion[rid][1][0]] = True
            msg_counts[requestion[rid][1][0]] = 0
            username[requestion[rid][1][0]] = "UNKNOWN"
            requestion[rid][0].setblocking(0)

            requestion[rid][0].setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True)

            # 对于 Linux 系统，请将下面的代码解除注释，注释下面的 3 行代码注释，直接运行。
            """
            requestion[rid][0].setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 180 * 60)
            requestion[rid][0].setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30)
            """
            
            requestion[rid][0].ioctl(socket.SIO_KEEPALIVE_VALS, (
                1, 180 * 1000, 30 * 1000
            ))

            conn.append(requestion[rid][0])
            address.append(requestion[rid][1])
            requestion[rid][0].send(bytes("[系统提示] 房主已准许您加入聊天室\n", encoding="utf-8"))
            flush_txt += f"[{time_str()}] <{rid}> User {requestion[rid][1]} was accepted to enter in the chatting room.\n"
            print(f"您准许了第 {rid} 号请求，用户 {requestion[rid][1]} 进入聊天室。")
            requestion[rid] = None
        except:
            print(f"[Error] 第 {rid} 次准许操作失败")
    
    def do_accept(self, arg):
        """
        使用方法（~ 表示 accept）：
            ~ <rid1> <rid2> <rid3> ... <ridk> 准许第 rid1,rid2,rid3,...,ridk 号进入请求
        """
        arg = arg.split(' ')
        for v in arg:
            try:
                i = int(v)
                if i >= len(requestion):
                    raise
                if not requestion[i]:
                    raise
            except:
                print("[Error] 参数错误或请求已被处理")
                return
        
        for v in arg:
            self.accept(int(v))
    
    def do_reject(self, arg):
        """
        使用方法（~ 表示 reject）：
            ~ <rid1> <rid2> <rid3> ... <ridk> 拒绝第 rid1,rid2,rid3,...,ridk 号进入请求
        """
        arg = arg.split(' ')
        for i in arg:
            try:
                i = int(i)
                if i >= len(requestion):
                    raise
                if not requestion[i]:
                    raise
            except:
                print("[Error] 参数错误或请求已被处理")
                return
        for i in arg:
            self.reject(int(i))
    
    def do_broadcast(self, arg):
        """
        使用方法（~ 表示 broadcast)：
            ~ <msg> 向全体成员广播信息 msg
        """    
        global flush_txt
        flush_txt += f"[{time_str()}] You broadcasted msg '{arg}'\n"
        for j in range(len(conn)):
            try:
                conn[j].send(bytes("[房主广播] " + arg + '\n', encoding="utf-8"))
                if_online[address[j][0]] = True
            except:
                print(f"向用户 {address[j]} (用户名 {username[address[j][0]]}) 广播失败。")
                if_online[address[j][0]] = False
                continue
        print("广播成功")

    def do_search(self, arg):
        """
        使用方法（~ 表示 search）：
            ~ ip <*ip>              搜索所有 ip 为 *ip 的用户信息，支持正则。
            ~ user <*user>          搜索所有 username 为 *user 的用户信息（支持正则）
            ~ online                搜索所有在线的用户的信息
            ~ offline               搜索所有离线的用户的信息
            ~ banned                查询所有被 ban 的用户的信息   
            ~ send_times <*times>   搜索所有发送信息次数大于等于 times 的用户的信息（按发送次数从大到小输出）
        """ 
        attributes = ["ip", "user", "online", "offline", "send_times", "banned"]
        arg = arg.split(' ')
        if (arg[0] not in attributes):
            print("[Error] 参数错误")
            return

        search_lst = []
        if (arg[0] == 'ip'):
            if len(arg) != 2:
                print("[Error] 参数错误")
                return
            search_lst.append(arg[1])
        
        if arg[0] == "user":
            if len(arg) != 2:
                print("[Error] 参数错误")
                return
            for i in address:
                ip = i[0]
                if re.search(arg[1], username[ip]):
                    search_lst.append(ip)
        
        if arg[0] == "online":
            for i in address:
                ip = i[0]
                if if_online[ip]:
                    search_lst.append(ip)
            search_lst.sort(key=lambda x : msg_counts[x]) 
            search_lst.reverse()
        
        if arg[0] == 'offline':
            for i in address:
                ip = i[0]
                if not if_online[ip]:
                    search_lst.append(ip)
        
        if arg[0] == "banned":
            for i in address:
                ip = i[0]
                if ip in ban_ip_lst:
                    search_lst.append(ip)
            self.print_user(search_lst)
            return
        
        if arg[0] == "send_times":
            if len(arg) != 2:
                print("[Error] 参数错误")
                return
            try:
                arg[1] = int(arg[1])
                if arg[1] < 0:
                    raise
            except:
                print("[Error] <*times> 必须是非负整数")
            for i in address:
                ip = i[0]
                if msg_counts[ip] >= arg[1]:
                    search_lst.append(ip)
            search_lst = list(set(search_lst))
            search_lst.sort(key = lambda x : msg_counts[x])
            search_lst.reverse()
            self.print_user(search_lst)
            return
        
        search_lst = list(set(search_lst))
        self.print_user(search_lst)

    def do_flush(self, arg):
        """
        输出缓冲区内容
        """
        global flush_txt
        with open("./log.txt", "a+", encoding="utf-8") as file:
            file.write(flush_txt)
        flush_txt = ""
    
    def do_exit(self, arg):
        """
        退出当前程序
        """
        self.do_flush(...)
        global EXIT_FLG
        EXIT_FLG = 1
        exit()
    
server = Server()
threading.Thread(target=server.cmdloop).start()
threading.Thread(target=receive_msg).start()
threading.Thread(target=add_accounts).start()