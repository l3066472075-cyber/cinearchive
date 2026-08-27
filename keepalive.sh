#!/bin/sh
# 影境档案保活：每5分钟ping一次，防止Render免费档休眠
curl -s -o /dev/null --max-time 30 https://cinearchive.onrender.com/api/v1/health
