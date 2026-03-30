from openai import OpenAI
import os

client = OpenAI(
    api_key='sk-AmgVktECHpmqe0bnM9YvMbozyzEzf7spz7nyuEk7SuUBbnUH',
    base_url="https://api.moonshot.cn/v1"
)

# 列出所有模型
models = client.models.list()
for model in models.data:
    print(f"{model.id}: {model.owned_by}")