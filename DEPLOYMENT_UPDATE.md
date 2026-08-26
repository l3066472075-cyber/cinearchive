# 影境档案 - 部署更新说明

## 📱 手机端问题修复

### 问题分析
手机端显示"应用错误"的主要原因：
1. **微信登录自动跳转失败** - 在微信环境中自动尝试微信登录，如果后端配置不正确会导致页面无法正常加载
2. **初始化错误处理不当** - 如果API调用失败（如主题加载、访客登录），会阻塞整个页面渲染
3. **移动端网络不稳定** - 移动网络环境下API请求可能失败，但前端没有合适的容错处理

### 修复内容
1. **增强错误处理** - 初始化过程增加try-catch，即使某些功能失败也不影响页面基本使用
2. **微信登录优化** - 增加跳转失败后的回退机制，避免陷入登录循环
3. **延迟加载** - 将访客登录延迟执行，不阻塞页面首次渲染
4. **友好错误提示** - 添加移动端友好的错误提示样式

### 技术细节
```javascript
// 修复后的初始化流程
(async function init() {
  try {
    handleMpLogin();           // 处理微信登录，增加容错
    observeReveal(document);   // 页面动画
    try {
      await loadGuideThemes(); // 加载主题，失败不影响其他功能
    } catch (e) {
      console.warn("加载主题失败", e);
    }
    setTimeout(() => {
      ensureGuestLogin();      // 延迟访客登录
    }, 500);
    if (getToken()) $("#login-btn").textContent = "已登录 ✓";
  } catch (e) {
    console.error("初始化错误", e);
    // 显示友好提示但不阻止页面使用
  }
})();
```

## 🤖 智谱AI API配置

### 方式一：本地快速配置（推荐开发测试）

```bash
cd cinelib/backend
./configure_zhipu.sh
# 输入智谱AI API密钥
```

### 方式二：手动配置

1. **创建 `.env` 文件**：
```bash
cd cinelib/backend
cp .env.zhipu.example .env
```

2. **编辑 `.env` 文件，填入API密钥**：
```env
LLM_API_KEY=你的智谱API密钥
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-4-flash

EMBEDDING_API_KEY=你的智谱API密钥
EMBEDDING_BASE_URL=https://open.bigmodel.cn/api/paas/v4
EMBEDDING_MODEL=embedding-2

# 其他配置...
```

3. **重启本地服务**：
```bash
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### 方式三：Render生产环境配置

1. **访问Render控制台**：
   - 打开 https://dashboard.render.com/
   - 找到 `cinearchive` 服务

2. **配置环境变量**：
   - 点击 `Environment` 标签页
   - 添加/更新以下环境变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `LLM_API_KEY` | 你的智谱API密钥 | 大模型调用密钥 |
| `EMBEDDING_API_KEY` | 你的智谱API密钥 | 嵌入模型调用密钥（可相同） |

3. **触发重新部署**：
   - 点击 `Save Changes`
   - Render会自动重新部署服务

## 🧪 测试验证

### 本地测试
```bash
# 1. 配置API密钥
cd cinelib/backend
./configure_zhipu.sh

# 2. 重启服务
.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# 3. 访问健康检查
curl http://127.0.0.1:8000/api/v1/health

# 预期输出：llm_enabled=true, embedding_enabled=true
```

### 线上测试
```bash
# 1. 在Render配置环境变量后，等待部署完成

# 2. 访问健康检查
curl https://cinearchive.onrender.com/api/v1/health

# 预期输出：llm_enabled=true, embedding_enabled=true

# 3. 测试推荐功能
curl -X POST https://cinearchive.onrender.com/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"query":"我现在很焦虑，工作让我很累"}'
```

## 📱 移动端测试建议

### 浏览器测试
1. **手机浏览器**：Safari、Chrome等
2. **微信内置浏览器**：发送链接到微信，在微信中打开
3. **不同网络环境**：WiFi、4G、5G

### 检查要点
- ✅ 页面能正常加载
- ✅ 推荐功能正常工作
- ✅ 登录功能（如果配置了微信）
- ✅ 电影详情查看
- ✅ 导航和交互流畅

## 🚀 部署更新

### 本地代码更新
```bash
cd cinelib
git pull origin main
cd backend
./configure_zhipu.sh  # 如果需要配置API
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### Render自动部署
```bash
# 1. 提交本地修改
cd cinelib
git add -A
git commit -m "更新描述"
git push origin main

# 2. Render会自动检测到push并触发部署
# 访问 https://dashboard.render.com/ 查看部署状态
```

## 🎯 下一步

1. **获取智谱AI API密钥**：
   - 访问 https://open.bigmodel.cn/
   - 注册/登录账户
   - 在控制台获取API密钥

2. **配置API密钥**：
   - 本地开发：使用配置脚本
   - 生产环境：在Render设置环境变量

3. **测试验证**：
   - 本地测试功能
   - 部署到Render测试
   - 手机端验证

4. **功能优化**：
   - 根据实际使用情况调整推荐算法
   - 优化移动端用户体验
   - 添加更多电影和标签

## 📞 技术支持

如果遇到问题：
1. 检查API密钥是否正确配置
2. 查看浏览器控制台错误信息
3. 检查Render服务日志
4. 确认网络连接正常

---

**祝部署顺利！🎉**