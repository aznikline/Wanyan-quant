# Rock Quant 部署指南

## 部署方式对比

### 方式1：Streamlit Community Cloud（推荐 ⭐⭐⭐⭐⭐）
最简单、最稳定的部署方式，完全免费，专门为 Streamlit 优化

**步骤：**
1. 访问 https://share.streamlit.io/
2. 用 GitHub 账号登录
3. 点击 "New app"
4. 选择你的仓库：`aznikline/Wanyan-quant`
5. 主文件路径：`Home.py`
6. 点击 "Deploy"

**优点：**
- 完全免费
- 自动部署，git push 自动更新
- 原生 Streamlit 性能优化
- 无需任何配置

---

### 方式2：Vercel 部署

**注意：Vercel 主要面向静态网站和 Serverless 函数，对 Streamlit 这种长连接应用支持有限，推荐使用方式1**

**步骤：**

1. 安装 Vercel CLI：
```bash
npm i -g vercel
```

2. 登录 Vercel：
```bash
vercel login
```

3. 部署：
```bash
vercel --prod
```

**配置已包含：**
- `vercel.json` - Vercel 配置文件

---

### 方式3：Docker 部署（本地/服务器部署 ⭐⭐⭐⭐）

创建 `Dockerfile`：
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**构建运行：**
```bash
docker build -t rock-quant .
docker run -p 8501:8501 rock-quant
```

---

### 方式4：PyWebIO 转换为纯网页（最适合 Vercel ⭐⭐⭐⭐）

如果需要部署到纯静态环境，可以考虑将 Streamlit 重写为 FastAPI + PyWebIO

---

## 快速部署建议

**立即开始的最佳选择：Streamlit Community Cloud**

1. 打开 https://share.streamlit.io/
2. 30秒完成部署
3. 获得永久域名：`rock-quant.streamlit.app`

**后续如果需要自定义域名：**
- Streamlit Community Cloud 支持绑定自定义域名
- 或者迁移到云服务器（阿里云、腾讯云、AWS等）

---

## 环境变量

如果使用 Tushare 数据源，需要设置环境变量：
```
TUSHARE_TOKEN=your_token_here
```

在 Streamlit Community Cloud 中，可以在部署时的 "Advanced settings" 中设置环境变量。
