#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查导出功能的环境配置
"""

import os
import sys

def check_experiments_dir():
    """检查实验目录"""
    print("=" * 60)
    print("检查1: 实验目录")
    print("=" * 60)
    
    if os.path.exists('experiments'):
        print("✅ experiments/ 目录存在")
        
        # 列出所有实验
        experiments = [d for d in os.listdir('experiments') if os.path.isdir(os.path.join('experiments', d))]
        print(f"✅ 找到 {len(experiments)} 个实验")
        
        for exp in experiments:
            exp_path = os.path.join('experiments', exp)
            print(f"\n实验: {exp}")
            
            # 检查元信息
            metadata_file = os.path.join(exp_path, 'metadata.json')
            if os.path.exists(metadata_file):
                print("  ✅ metadata.json 存在")
                import json
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    print(f"     名称: {metadata.get('experiment_name')}")
                    print(f"     场景: {metadata.get('scenario_type')}")
            else:
                print("  ❌ metadata.json 不存在")
            
            # 检查数据库
            db_file = os.path.join(exp_path, 'database.db')
            if os.path.exists(db_file):
                size = os.path.getsize(db_file)
                print(f"  ✅ database.db 存在 ({size:,} 字节)")
            else:
                print("  ❌ database.db 不存在")
            
            # 检查认知记忆
            cognitive_dir = os.path.join(exp_path, 'cognitive_memory')
            if os.path.exists(cognitive_dir):
                files = [f for f in os.listdir(cognitive_dir) if f.endswith('.json')]
                print(f"  ✅ cognitive_memory/ 存在 ({len(files)} 个文件)")
            else:
                print("  ⚠️  cognitive_memory/ 不存在")
        
        return len(experiments) > 0
    else:
        print("❌ experiments/ 目录不存在")
        print("💡 提示：请先保存至少一个实验")
        return False

def check_flask_version():
    """检查Flask版本"""
    print("\n" + "=" * 60)
    print("检查2: Flask 版本")
    print("=" * 60)
    
    try:
        import flask
        version = flask.__version__
        print(f"✅ Flask 版本: {version}")
        
        major_version = int(version.split('.')[0])
        if major_version >= 2:
            print("✅ Flask 2.0+，使用 download_name 参数")
        else:
            print("✅ Flask 1.x，使用 attachment_filename 参数")
        
        return True
    except ImportError:
        print("❌ Flask 未安装")
        print("💡 提示：运行 pip install flask")
        return False

def check_dependencies():
    """检查依赖包"""
    print("\n" + "=" * 60)
    print("检查3: 依赖包")
    print("=" * 60)
    
    required_packages = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'sqlite3': 'SQLite3 (内置)',
    }
    
    all_ok = True
    for module, name in required_packages.items():
        try:
            if module == 'sqlite3':
                import sqlite3
            else:
                __import__(module)
            print(f"✅ {name} 已安装")
        except ImportError:
            print(f"❌ {name} 未安装")
            all_ok = False
    
    return all_ok

def check_backend_running():
    """检查后端是否运行"""
    print("\n" + "=" * 60)
    print("检查4: 后端服务")
    print("=" * 60)
    
    try:
        import requests
        response = requests.get('http://localhost:3000/api/experiments', timeout=2)
        print(f"✅ 后端服务正在运行")
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            exp_count = len(data.get('experiments', []))
            print(f"   实验数量: {exp_count}")
        
        return True
    except requests.exceptions.ConnectionError:
        print("❌ 后端服务未运行")
        print("💡 提示：运行 python frontend_api.py")
        return False
    except ImportError:
        print("⚠️  requests 包未安装，跳过检查")
        print("💡 提示：运行 pip install requests")
        return None
    except Exception as e:
        print(f"⚠️  检查失败: {e}")
        return None

def check_export_route():
    """检查导出路由"""
    print("\n" + "=" * 60)
    print("检查5: 导出路由")
    print("=" * 60)
    
    # 检查 frontend_api.py 中是否有导出路由
    if os.path.exists('frontend_api.py'):
        with open('frontend_api.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if '/export' in content and 'export_experiment' in content:
                print("✅ 导出路由已定义")
                
                # 检查是否有兼容性处理
                if 'download_name' in content and 'attachment_filename' in content:
                    print("✅ Flask 版本兼容性处理已添加")
                else:
                    print("⚠️  可能缺少 Flask 版本兼容性处理")
                
                return True
            else:
                print("❌ 导出路由未定义")
                return False
    else:
        print("❌ frontend_api.py 文件不存在")
        return False

def main():
    print("开始检查导出功能环境配置")
    print()
    
    results = {
        '实验目录': check_experiments_dir(),
        'Flask版本': check_flask_version(),
        '依赖包': check_dependencies(),
        '后端服务': check_backend_running(),
        '导出路由': check_export_route()
    }
    
    print("\n" + "=" * 60)
    print("检查结果汇总")
    print("=" * 60)
    
    for name, result in results.items():
        if result is True:
            status = "✅ 通过"
        elif result is False:
            status = "❌ 失败"
        else:
            status = "⚠️  跳过"
        print(f"{name}: {status}")
    
    # 总体评估
    print("\n" + "=" * 60)
    failed_count = sum(1 for r in results.values() if r is False)
    
    if failed_count == 0:
        print("✅ 所有检查通过！导出功能应该可以正常工作")
        print("\n下一步：")
        print("1. 确保后端服务正在运行: python frontend_api.py")
        print("2. 确保前端服务正在运行: cd frontend && npm run dev")
        print("3. 打开浏览器测试导出功能")
    else:
        print(f"❌ 发现 {failed_count} 个问题，请先解决这些问题")
        print("\n建议：")
        if not results['实验目录']:
            print("- 先保存至少一个实验")
        if not results['Flask版本']:
            print("- 安装 Flask: pip install flask")
        if not results['依赖包']:
            print("- 安装依赖: pip install -r requirements.txt")
        if results['后端服务'] is False:
            print("- 启动后端: python frontend_api.py")
        if not results['导出路由']:
            print("- 检查 frontend_api.py 是否包含导出路由代码")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
