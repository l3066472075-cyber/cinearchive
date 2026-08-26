#!/bin/bash
# 影境档案 - 智谱API配置脚本

echo "=========================================="
echo "  影境档案 - 智谱AI配置向导"
echo "=========================================="
echo ""
echo "这个脚本将帮助你配置智谱AI API密钥"
echo ""

# 询问API密钥
echo "请输入智谱AI的API密钥（可以在 https://open.bigmodel.cn/ 获取）："
read -s API_KEY
echo ""

if [ -z "$API_KEY" ]; then
    echo "错误：API密钥不能为空"
    exit 1
fi

# 创建或更新.env文件
cat > .env << EOF
# 智谱AI配置
LLM_API_KEY=${API_KEY}
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-4-flash

# 嵌入模型配置（智谱）
EMBEDDING_API_KEY=${API_KEY}
EMBEDDING_BASE_URL=https://open.bigmodel.cn/api/paas/v4
EMBEDDING_MODEL=embedding-2

# 微信登录配置（留空使用开发模式）
WX_APPID=
WX_APP_SECRET=

# JWT配置
JWT_SECRET=cinelib-production-secret-change-me
JWT_EXPIRE_MINUTES=10080
EOF

echo "✓ .env文件已创建/更新"
echo ""
echo "配置内容："
echo "  - 大模型API密钥: ${API_KEY:0:8}***"
echo "  - 大模型API地址: https://open.bigmodel.cn/api/paas/v4"
echo "  - 大模型: glm-4-flash"
echo "  - 嵌入模型: embedding-2"
echo ""

echo "=========================================="
echo "  配置完成！"
echo "=========================================="
echo ""
echo "本地测试："
echo "  1. 重启本地服务：.venv/bin/python -m uvicorn app.main:app --reload --port 8000"
echo "  2. 访问：http://127.0.0.1:8000/"
echo ""
echo "Render部署（需要设置环境变量）："
echo "  1. 访问Render控制台: https://dashboard.render.com/"
echo "  2. 找到 cinearchive 服务"
echo "  3. 进入 Environment 标签页"
echo "  4. 添加/更新以下环境变量："
echo "     - LLM_API_KEY = ${API_KEY}"
echo "     - EMBEDDING_API_KEY = ${API_KEY}"
echo "  5. 点击 'Save Changes' 触发重新部署"
echo ""