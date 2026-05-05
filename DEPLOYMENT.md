# 🚀 Rock Quant 部署指南

## 推荐部署方案

### 方案1：Streamlit Community Cloud（推荐，零配置）

**优势：**
- ✅ 完全免费
- ✅ 一键部署，无需配置
- ✅ 自动HTTPS
- ✅ 自动更新（GitHub push后自动部署）
- ✅ 原生支持Streamlit长连接

**部署步骤：**
1. 访问：https://share.streamlit.io/
2. 使用GitHub账号登录
3. 点击 "New app"
4. 选择仓库：aznikline/Wanyan-quant
5. 分支：main
6. 主文件路径：app.py
7. 点击 "Deploy"

**部署时间**：约2-5分钟

---

### 方案2：Vercel部署（需要额外配置）

**注意**：Streamlit是有状态的长连接应用，Vercel的Serverless架构不太适合，可能会遇到连接超时问题。建议使用方案1。

如果仍需Vercel部署：

1. 访问：https://vercel.com/new
2. 导入仓库：aznikline/Wanyan-quant
3. 配置构建命令：`pip install -r requirements.txt`
4. 配置启动命令：`streamlit run app.py --server.port 8501 --server.headless true`
5. 点击部署

**已知限制**：
- Vercel Serverless函数最大执行时间10秒
- WebSocket连接可能不稳定
- 冷启动时间较长

---

### 方案3：本地服务器部署

```bash
# 克隆代码
git clone https://github.com/aznikline/Wanyan-quant.git
cd Wanyan-quant

# 安装依赖
pip install -r requirements.txt

# 启动服务
streamlit run app.py --server.port 8501
```

**使用Nginx反向代理（生产环境）**：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 方案4：Docker部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.headless=true"]
```

```bash
# 构建并运行
docker build -t rockquant .
docker run -p 8501:8501 rockquant
```

---

## 部署验证

部署完成后，访问应用，测试以下功能：

1. ✅ 新手引导正常显示
2. ✅ 侧边栏配置可用
3. ✅ 点击"运行回测"正常执行
4. ✅ 净值曲线和图表正常渲染
5. ✅ 交易明细表格正常显示
6. ✅ CSV导出功能正常

---

## GitHub仓库

**仓库地址**：https://github.com/aznikline/Wanyan-quant

**当前状态**：✅ 代码已推送，可直接部署

---

## 环境变量配置

无需特殊环境变量，所有配置均已内置。如需对接实盘行情：

- TUSHARE_TOKEN：Tushare API Token
- AK_SHARE_TOKEN：Akshare API Token

在Streamlit后台设置Secrets即可。
