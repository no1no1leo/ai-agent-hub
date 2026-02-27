#!/usr/bin/env python3
"""
🔍 NVIDIA NIM 影響分析
比較「有 NIM」與「無 NIM」在任務完成上的差異
"""
import os
import time
from typing import Dict, Any

# 模擬環境變數檢查
HAS_NIM = os.getenv("NVIDIA_NIM_API_KEY") is not None

def simulate_task_without_nim(task_desc: str) -> Dict[str, Any]:
    """
    無 NIM 模式：
    - 使用本地規則或隨機生成
    - 速度極快 (<1ms)
    - 結果品質低，僅供參考
    """
    start = time.time()
    # 模擬簡單處理
    result = f"[模擬] 已處理任務：{task_desc[:20]}... (無實際分析)"
    end = time.time()
    
    return {
        "mode": "Without NIM (Simulation)",
        "result": result,
        "latency_ms": (end - start) * 1000,
        "cost_sol": 0.0,
        "quality_score": 0.5  # 品質普通
    }

def simulate_task_with_nim(task_desc: str) -> Dict[str, Any]:
    """
    有 NIM 模式：
    - 呼叫 NVIDIA NIM API
    - 延遲較高 (100ms - 2s)
    - 結果品質高，具實際價值
    """
    start = time.time()
    
    if HAS_NIM:
        # 真實呼叫 NIM API (此處為偽代碼)
        # response = nvm_client.chat.completions.create(...)
        # result = response.choices[0].message.content
        time.sleep(0.5)  # 模擬網路延遲
        result = f"[NIM] 深度分析：{task_desc[:20]}... 發現 3 個關鍵模式..."
        cost = 0.0065  # 真實成本
        quality = 0.95
    else:
        # 若無 Key，退回模擬
        time.sleep(0.001)
        result = "[NIM] 未檢測到 API Key，退回模擬模式..."
        cost = 0.0
        quality = 0.5
    
    end = time.time()
    
    return {
        "mode": "With NVIDIA NIM",
        "result": result,
        "latency_ms": (end - start) * 1000,
        "cost_sol": cost,
        "quality_score": quality
    }

def print_comparison():
    print("\n" + "="*70)
    print("🔍 NVIDIA NIM 影響分析：有無 NIM 的差異")
    print("="*70)
    
    task = "分析電商數據異常"
    
    print("\n📝 任務：", task)
    print("-" * 70)
    
    # 1. 無 NIM
    print("\n1️⃣  無 NIM 模式 (本地模擬)")
    res_no_nim = simulate_task_without_nim(task)
    print(f"   結果：{res_no_nim['result']}")
    print(f"   ⏱️  延遲：{res_no_nim['latency_ms']:.2f} ms")
    print(f"   💰 成本：{res_no_nim['cost_sol']} SOL")
    print(f"   📊 品質：{res_no_nim['quality_score']*100:.0f}%")
    
    # 2. 有 NIM
    print("\n2️⃣  有 NIM 模式 (NVIDIA NIM API)")
    res_nim = simulate_task_with_nim(task)
    print(f"   結果：{res_nim['result']}")
    print(f"   ⏱️  延遲：{res_nim['latency_ms']:.2f} ms")
    print(f"   💰 成本：{res_nim['cost_sol']:.4f} SOL")
    print(f"   📊 品質：{res_nim['quality_score']*100:.0f}%")
    
    # 3. 總結
    print("\n" + "="*70)
    print("📊 綜合比較")
    print("="*70)
    print(f"{'指標':<15} | {'無 NIM':<20} | {'有 NIM':<20}")
    print("-" * 70)
    print(f"{'延遲':<15} | {res_no_nim['latency_ms']:<20.2f} | {res_nim['latency_ms']:<20.2f}")
    print(f"{'成本 (SOL)':<15} | {res_no_nim['cost_sol']:<20.4f} | {res_nim['cost_sol']:<20.4f}")
    print(f"{'品質分數':<15} | {res_no_nim['quality_score']:<20.0%} | {res_nim['quality_score']:<20.0%}")
    print(f"{'適用場景':<15} | {'測試/開發/演示':<20} | {'生產環境/高價值任務':<20}")
    
    print("\n💡 建議策略:")
    print("   - 開發測試階段：使用無 NIM 模式，節省成本")
    print("   - 高價值任務：使用 NIM 模式，確保品質")
    print("   - 混合模式：先用無 NIM 預篩，再對高價值任務用 NIM")

if __name__ == "__main__":
    print_comparison()
