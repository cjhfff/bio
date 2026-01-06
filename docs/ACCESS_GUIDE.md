# 访问地址说明

本文档说明部署后如何访问智能论文推送系统。

## 📍 访问地址

### 本地访问（开发环境）

如果您在本地电脑运行系统：

```
前端界面: http://localhost:3000
后端API: http://localhost:8000
API文档: http://localhost:8000/docs
```

### 远程访问（服务器部署）

如果您将系统部署在服务器上，需要通过服务器的IP地址或域名访问：

#### 使用IP地址访问

```
前端界面: http://<服务器IP地址>:3000
后端API: http://<服务器IP地址>:8000
API文档: http://<服务器IP地址>:8000/docs
```

**示例：**
- 如果服务器IP是 `192.168.1.100`，则访问：
  - 前端：`http://192.168.1.100:3000`
  - 后端：`http://192.168.1.100:8000`

#### 使用域名访问（推荐）

如果您有域名，配置后可以使用域名访问：

```
前端界面: http://your-domain.com
后端API: http://your-domain.com/api
```

需要配置Nginx等反向代理，参考下方配置示例。

## 🔍 如何找到您的服务器IP地址

### 在服务器上查看

登录到服务器后，运行以下命令：

```bash
# Linux
ip addr show | grep inet
# 或者
hostname -I

# 查看公网IP（如果需要外网访问）
curl ifconfig.me
```

### 在云服务商控制台查看

- **阿里云**：进入ECS实例，查看"公网IP"
- **腾讯云**：进入云服务器，查看"主IP地址"
- **AWS**：进入EC2实例，查看"公有IPv4地址"

## 🚪 端口说明

系统使用以下端口：

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 3000 | Vue.js Web界面 |
| 后端 | 8000 | FastAPI后端服务 |

**重要：** 确保防火墙允许这些端口的入站访问！

## 🔓 开放防火墙端口

### Ubuntu/Debian

```bash
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
sudo ufw reload
```

### CentOS/RHEL

```bash
sudo firewall-cmd --add-port=3000/tcp --permanent
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

### 云服务器安全组

还需要在云服务商控制台配置安全组规则：

**入站规则：**
- 协议：TCP
- 端口：3000, 8000
- 来源：0.0.0.0/0（允许所有IP）或指定IP段

## 🌐 不同部署方式的访问地址

### 1. Docker 部署

启动服务后：

```bash
cd docker
docker-compose up -d
```

**访问地址：**
- 本地：`http://localhost:3000`
- 远程：`http://<服务器IP>:3000`

### 2. 手动部署

分别启动后端和前端：

```bash
# 终端1 - 后端
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# 终端2 - 前端
cd frontend
npm run dev -- --host 0.0.0.0
```

**访问地址：**
- 本地：`http://localhost:3000`
- 远程：`http://<服务器IP>:3000`

### 3. 使用 Nginx 反向代理（生产环境推荐）

配置Nginx后可以使用80端口（HTTP）或443端口（HTTPS）访问，无需指定端口号。

**Nginx 配置示例：**

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 改为您的域名或IP

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 后端API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # API文档
    location /docs {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

配置后访问：
- 前端：`http://your-domain.com`
- 后端API：`http://your-domain.com/api`
- API文档：`http://your-domain.com/docs`

## 📱 移动设备访问

确保手机/平板与服务器在同一网络（或服务器有公网IP），在浏览器输入：

```
http://<服务器IP>:3000
```

## ✅ 验证访问

### 1. 检查服务是否运行

```bash
# 检查端口监听
netstat -tlnp | grep 3000
netstat -tlnp | grep 8000

# 或使用 ss
ss -tlnp | grep 3000
ss -tlnp | grep 8000
```

应该看到类似输出：
```
tcp   0   0 0.0.0.0:3000   0.0.0.0:*   LISTEN
tcp   0   0 0.0.0.0:8000   0.0.0.0:*   LISTEN
```

### 2. 测试后端API

```bash
# 从服务器本地测试
curl http://localhost:8000/health

# 从其他机器测试
curl http://<服务器IP>:8000/health
```

应该返回：
```json
{"status":"healthy"}
```

### 3. 测试前端访问

在浏览器打开：
- 本地：`http://localhost:3000`
- 远程：`http://<服务器IP>:3000`

应该能看到系统界面。

## 🛠️ 故障排查

### 无法访问前端（3000端口）

1. **检查前端服务是否启动**
   ```bash
   docker ps | grep frontend
   # 或
   ps aux | grep vite
   ```

2. **检查端口绑定**
   ```bash
   netstat -tlnp | grep 3000
   ```
   确保绑定到 `0.0.0.0:3000` 而不是 `127.0.0.1:3000`

3. **检查防火墙**
   ```bash
   sudo ufw status | grep 3000
   ```

### 无法访问后端（8000端口）

1. **检查后端服务是否启动**
   ```bash
   docker ps | grep backend
   # 或
   ps aux | grep uvicorn
   ```

2. **查看后端日志**
   ```bash
   docker logs bio-backend
   # 或查看日志文件
   tail -f data/logs/paper_push.log
   ```

### 可以访问但功能不正常

1. **打开浏览器开发者工具**（F12）
2. **查看 Console 标签** 是否有错误
3. **查看 Network 标签** 检查API请求是否正常

常见问题：
- API请求404：检查后端服务是否正常启动
- CORS错误：检查后端CORS配置
- 连接超时：检查防火墙和网络连接

## 🔒 安全建议

1. **不要在公网暴露开发服务器**
   - 开发服务器（`npm run dev`）仅用于开发
   - 生产环境使用生产构建：`npm run build` + Nginx

2. **使用HTTPS**
   - 配置SSL证书（Let's Encrypt免费）
   - Nginx配置HTTPS

3. **限制访问来源**
   - 防火墙只允许特定IP访问
   - 或添加HTTP基本认证

4. **使用强密码**
   - API密钥不要暴露
   - 定期更换密钥

## 📞 需要帮助？

如果遇到访问问题：

1. 检查服务是否正常运行
2. 检查防火墙规则
3. 查看系统日志
4. 参考本文档的故障排查部分

---

**快速参考卡片：**

```
┌─────────────────────────────────────┐
│  访问地址速查                        │
├─────────────────────────────────────┤
│  本地前端： http://localhost:3000   │
│  本地后端： http://localhost:8000   │
│                                      │
│  远程前端： http://<IP>:3000        │
│  远程后端： http://<IP>:8000        │
│                                      │
│  API文档： /docs                     │
└─────────────────────────────────────┘
```
