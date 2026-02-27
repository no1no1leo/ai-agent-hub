#!/usr/bin/env python3
"""
🖼️ 多模態任務演示
發布一個帶有圖片的任務，測試 Agent 是否能識別圖片內容
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

API_URL = "https://ai-agent-hub.onrender.com"

def post_image_task():
    print("🖼️ 發布一個多模態任務：識別圖片內容")
    
    # 使用一個公開的測試圖片 URL
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/320px-Cat_November_2010-1a.jpg"
    
    payload = {
        "description": "請描述這張圖片中的內容，並判斷這是什麼動物。",
        "input_data": "image_analysis_task",
        "max_budget": 0.5,
        "expected_tokens": 1000,
        "requester_id": "multimodal_tester",
        "image_url": image_url
    }
    
    print(f"📤 發送請求到 {API_URL}/tasks ...")
    response = requests.post(f"{API_URL}/tasks", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 任務發布成功！")
        print(f"   任務 ID: {data['task_id']}")
        print(f"   描述：{data['description']}")
        print(f"\n🌐 請前往儀表板查看：{API_URL}/")
        print(f"   你應該看得到貓咪的圖片！")
    else:
        print(f"❌ 發布失敗：{response.text}")

if __name__ == "__main__":
    post_image_task()
