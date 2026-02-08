import socket
import sys
import os
import threading
import re
import ctypes
from urllib.parse import unquote
type_table={
    'html':"text/html",
    'css':"text/css",
    'js':"application/javascript",
    'json':"application/json",
    'png':"image/png",
    'jpg':"image/jpeg",
    'gif':"image/gif",
    'txt':"text/plain",
    'mp4':"video/mp4",
    'webm':"video/webm",
    'mp3':"audio/mpeg",
    'webp':"image/webp",
    'svg':"image/svg+xml",
    'xml':"application/xml",
    'zip':"application/x-zip-compressed",
    'rar':"application/x-compressed",
    '7z':"application/x-compressed"
}
def require_admin():
    """请求管理员权限，如果当前不是管理员，则直接提升权限"""
    if not ctypes.windll.shell32.IsUserAnAdmin():
        # 重新以管理员权限启动
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        
        # 使用ShellExecuteW以管理员身份运行
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            None,
            1
        )
        
        # 退出当前进程
        sys.exit(0)
def get_content_type(path):
    for ext in type_table:
        if path.endswith("."+ext):
            return type_table[ext]
    return "application/octet-stream"
def handle_client(client_socket, addr, foldpath):
    with client_socket:
        request=b""
        try:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                request += data
                if b"\r\n\r\n" in request:
                    break
                if b"Content-Length:" in request:
                    request_text = request.decode('utf-8', errors='ignore')
                    match = re.search(r'Content-Length:\s*(\d+)', request_text, re.IGNORECASE)
                    if match:
                        content_length = int(match.group(1))
                        header_end = request.find(b"\r\n\r\n")
                        body_start = header_end + 4
                        if len(request) - body_start >= content_length:
                            break
            text=request.decode("utf-8")
            if text.startswith("GET"):
                match = re.search(r'GET\s+(/.*?)\s+HTTP/1\.1', text)
                if match:
                    path=match.group(1)
                    path=path.lstrip("/")
                    path=path.split("?")[0].split("#")[0]
                    path=unquote(path)
                    path=os.path.join(foldpath,path)
                    if not path.startswith(foldpath):
                        if os.path.exists(os.path.join(foldpath,"403.html")):
                            with open(os.path.join(foldpath,"403.html"), "rb") as f:
                                response = f.read()
                                response_header = f"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\nContent-Length: {len(response)}\r\n\r\n".encode("utf-8")
                                response = response_header + response
                            client_socket.sendall(response)
                        else:
                            response = b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\ncharset=utf-8\r\n\r\nForbidden"
                            client_socket.sendall(response)
                        return

                    if os.path.exists(path) and os.path.isdir(path):
                        path=os.path.join(path,"index.html")
                    if os.path.exists(path):
                        with open(path, "rb") as f:
                            response = f.read()
                            response_header = f"HTTP/1.1 200 OK\r\nContent-Type: {get_content_type(path)}\r\nContent-Length: {len(response)}\r\n\r\n".encode("utf-8")
                            response = response_header + response
                            client_socket.sendall(response)
                    else:
                        if os.path.exists(os.path.join(foldpath,"404.html")):
                            with open(os.path.join(foldpath,"404.html"), "rb") as f:
                                response = f.read()
                                response_header = f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(response)}\r\n\r\n".encode("utf-8")
                                response = response_header + response
                                client_socket.sendall(response)
                        else:
                            response = b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\ncharset=utf-8\r\n\r\nNot Found"
                            client_socket.sendall(response)
        except Exception as e:
            print('Error:',e)
            response = b"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\ncharset=utf-8\r\n\r\nInternal Server Error"
            client_socket.sendall(response)
        
def launch_server():
    if len(sys.argv)==3:
        foldpath=sys.argv[1]
        port=int(sys.argv[2])
    elif len(sys.argv)==2:
        foldpath=sys.argv[1]
        port=8080
    else:
        print(f"Usage: {sys.argv[0]} <foldpath> [port]")
        sys.exit(1)
    require_admin()
    server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    if not os.path.exists(foldpath):
        print(f"Folder {foldpath} does not exist")
        sys.exit(1)
    server.bind(("0.0.0.0",port))
    server.listen(1)
    while True:
        client_socket, client_address = server.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address, foldpath))
        client_thread.start()

if __name__ == '__main__':
    launch_server()
