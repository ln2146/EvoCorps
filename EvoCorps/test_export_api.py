#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实验导出API
"""

import requests
import os

# 配置
API_BASE_URL = "http://localhost:3000/api"

def test_get_experiments():
    """测试获取实验列表"""
    print("=" * 60)
    print("测试1: 获取实验列表")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/experiments")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            experiments = data.get('experiments', [])
            print(f"✅ 成功获取 {len(experiments)} 个实验")
            
            for exp in experiments:
                print(f"\n实验ID: {exp['experiment_id']}")
                print(f"实验名称: {exp['experiment_name']}")
                print(f"场景类型: {exp['scenario_type']}")
                print(f"数据库已保存: {exp['database_saved']}")
            
            return experiments
        else:
            print(f"❌ 失败: {response.text}")
            return []
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []

def test_export_experiment(experiment_id):
    """测试导出实验"""
    print("\n" + "=" * 60)
    print(f"测试2: 导出实验 {experiment_id}")
    print("=" * 60)
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/experiments/{experiment_id}/export",
            stream=True
        )
        
        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            # 保存文件
            filename = f"{experiment_id}_export.zip"
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = os.path.getsize(filename)
            print(f"✅ 成功导出！")
            print(f"文件名: {filename}")
            print(f"文件大小: {file_size:,} 字节 ({file_size/1024:.2f} KB)")
            
            # 验证ZIP文件
            import zipfile
            try:
                with zipfile.ZipFile(filename, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    print(f"\nZIP文件包含 {len(file_list)} 个文件:")
                    for file in file_list[:10]:  # 只显示前10个
                        print(f"  - {file}")
                    if len(file_list) > 10:
                        print(f"  ... 还有 {len(file_list) - 10} 个文件")
                
                print("\n✅ ZIP文件格式正确")
            except Exception as e:
                print(f"\n❌ ZIP文件验证失败: {e}")
        else:
            print(f"❌ 失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("开始测试实验导出API")
    print("确保后端服务正在运行: python frontend_api.py")
    print()
    
    # 测试1: 获取实验列表
    experiments = test_get_experiments()
    
    if not experiments:
        print("\n⚠️  没有找到实验，请先保存一个实验")
        return
    
    # 测试2: 导出第一个实验
    first_experiment = experiments[0]
    test_export_experiment(first_experiment['experiment_id'])
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()
