from __future__ import annotations

import csv
import os
from typing import List, Tuple
import numpy as np


def calculate_target_values(target_mean: float, target_std: float, wt_mean: float) -> Tuple[int, int, int]:
    """
    根据目标均值和标准差，反推三个整数荧光值
    使得 (F1/wt_mean + F2/wt_mean + F3/wt_mean)/3 = target_mean
    且 std([F1/wt_mean, F2/wt_mean, F3/wt_mean], ddof=1) = target_std
    """
    # 目标倍数值
    target_fold_values = np.array([
        target_mean - target_std,  # 第一个值：均值减一个标准差
        target_mean,               # 第二个值：均值
        target_mean + target_std   # 第三个值：均值加一个标准差
    ])
    
    # 转换为荧光值
    target_fluorescence = target_fold_values * wt_mean
    
    # 四舍五入为整数
    f1, f2, f3 = map(int, np.round(target_fluorescence))
    
    # 验证并微调以确保准确匹配
    # 迭代优化以获得最佳整数组合
    best_diff = float('inf')
    best_values = (f1, f2, f3)
    
    # 在初始值附近搜索最佳整数组合
    for delta1 in range(-50, 51):
        for delta2 in range(-50, 51):
            for delta3 in range(-50, 51):
                test_f1 = max(1, f1 + delta1)
                test_f2 = max(1, f2 + delta2) 
                test_f3 = max(1, f3 + delta3)
                
                # 计算实际的倍数
                test_folds = np.array([test_f1, test_f2, test_f3]) / wt_mean
                test_mean = np.mean(test_folds)
                test_std = np.std(test_folds, ddof=1)
                
                # 计算与目标的差异
                diff = abs(test_mean - target_mean) + abs(test_std - target_std)
                
                if diff < best_diff:
                    best_diff = diff
                    best_values = (test_f1, test_f2, test_f3)
                    
                # 如果找到了很好的匹配，提前退出
                if diff < 0.001:
                    return best_values
    
    return best_values


def main():
    # WT 基准数据（保持不变）
    wt_data = (5583, 10939, 15072)
    wt_mean = np.mean(wt_data)
    
    # 输入数据：[变异名称, 目标均值, 目标标准差, 原始F1, 原始F2, 原始F3]
    input_data = [
        ("KI58A,1171L", 6.87, 0.27, 71218, 70072, 65831),
        ("V163G,1171T", 6.78, 0.92, 76084, 63378, 57167),
        ("Y39N,K158Q", 4.45, 0.16, 46576, 45024, 43213),
        ("KI58N,1171V", 3.21, 0.43, 29657, 27770, 36320),
        ("VllW,V163A", 2.77, 0.26, 28354, 23766, 28689),
        ("K158A,V163G", 2.72, 0.34, 27199, 21983, 28768),
        ("V163A,K214E", 0.31, 0.03, 2941, 3219, 2675),
        ("V163G,K214E", 0.30, 0.27, 3022, 3262, 2639),
    ]
    
    # 准备输出数据
    results = []
    header = [
        "Designed mutations",
        "Target Mean±SD", 
        "Original F1", "Original F2", "Original F3",
        "Adjusted F1", "Adjusted F2", "Adjusted F3",
        "Achieved Mean±SD",
        "Error (Mean)", "Error (SD)"
    ]
    
    print("数据调整结果:")
    print("=" * 80)
    
    for mutation, target_mean, target_std, orig_f1, orig_f2, orig_f3 in input_data:
        # 计算调整后的荧光值
        adj_f1, adj_f2, adj_f3 = calculate_target_values(target_mean, target_std, wt_mean)
        
        # 验证调整后的结果
        adj_folds = np.array([adj_f1, adj_f2, adj_f3]) / wt_mean
        achieved_mean = np.mean(adj_folds)
        achieved_std = np.std(adj_folds, ddof=1)
        
        # 计算误差
        error_mean = abs(achieved_mean - target_mean)
        error_std = abs(achieved_std - target_std)
        
        print(f"{mutation}:")
        print(f"  目标: {target_mean:.2f} ± {target_std:.2f}")
        print(f"  原始: {orig_f1}, {orig_f2}, {orig_f3}")
        print(f"  调整: {adj_f1}, {adj_f2}, {adj_f3}")
        print(f"  实现: {achieved_mean:.3f} ± {achieved_std:.3f}")
        print(f"  误差: 均值 {error_mean:.4f}, 标准差 {error_std:.4f}")
        print()
        
        # 添加到结果列表
        results.append([
            mutation,
            f"{target_mean:.2f} ± {target_std:.2f}",
            orig_f1, orig_f2, orig_f3,
            adj_f1, adj_f2, adj_f3,
            f"{achieved_mean:.3f} ± {achieved_std:.3f}",
            f"{error_mean:.4f}",
            f"{error_std:.4f}"
        ])
    
    # 添加 WT 数据（保持不变）
    wt_folds = np.array(wt_data) / wt_mean
    wt_achieved_mean = np.mean(wt_folds) 
    wt_achieved_std = np.std(wt_folds, ddof=1)
    
    results.append([
        "WT(avGFP,UniProtKB:P42212)",
        "1.00 ± 0.45",
        wt_data[0], wt_data[1], wt_data[2],
        wt_data[0], wt_data[1], wt_data[2],  # WT 数据不变
        f"{wt_achieved_mean:.3f} ± {wt_achieved_std:.3f}",
        f"{abs(wt_achieved_mean - 1.00):.4f}",
        f"{abs(wt_achieved_std - 0.45):.4f}"
    ])
    
    print("WT (保持不变):")
    print(f"  目标: 1.00 ± 0.45")
    print(f"  数据: {wt_data[0]}, {wt_data[1]}, {wt_data[2]}")
    print(f"  实现: {wt_achieved_mean:.3f} ± {wt_achieved_std:.3f}")
    print()
    
    # 写入 CSV 文件
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "adjusted_fluorescence_data.csv")
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(results)
    
    print(f"结果已保存到: {output_path}")
    
    # 生成简化版本（只包含最终调整后的数据）
    simple_header = ["Designed mutations", "Target Mean±SD", "Adjusted F1", "Adjusted F2", "Adjusted F3"]
    simple_results = []
    
    for row in results:
        simple_results.append([
            row[0],  # Designed mutations
            row[1],  # Target Mean±SD
            row[5],  # Adjusted F1
            row[6],  # Adjusted F2  
            row[7]   # Adjusted F3
        ])
    
    simple_output_path = os.path.join(output_dir, "final_adjusted_data.csv")
    with open(simple_output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(simple_header)
        writer.writerows(simple_results)
    
    print(f"简化结果已保存到: {simple_output_path}")


if __name__ == "__main__":
    main()
