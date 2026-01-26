#!/usr/bin/env node
/**
 * 开发环境启动脚本
 * 同时启动后端 API 和前端开发服务器
 */

import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  blue: '\x1b[34m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
};

function log(color, prefix, message) {
  console.log(`${color}${colors.bright}[${prefix}]${colors.reset} ${message}`);
}

// 启动后端 API
function startBackend() {
  log(colors.blue, 'Backend', '正在启动后端 API 服务...');
  
  const backendPath = path.join(__dirname, '..', 'frontend_api.py');
  const backend = spawn('python', [backendPath], {
    cwd: path.join(__dirname, '..'),
  });

  backend.stdout.on('data', (data) => {
    const output = data.toString().trim();
    if (output) {
      log(colors.blue, 'Backend', output);
    }
  });

  backend.stderr.on('data', (data) => {
    const output = data.toString().trim();
    if (output && !output.includes('WARNING') && !output.includes('Restarting')) {
      log(colors.red, 'Backend', output);
    }
  });

  backend.on('close', (code) => {
    if (code !== 0) {
      log(colors.red, 'Backend', `后端服务退出，代码: ${code}`);
      process.exit(1);
    }
  });

  return backend;
}

// 启动前端
function startFrontend() {
  // 等待 2 秒让后端启动
  setTimeout(() => {
    log(colors.green, 'Frontend', '正在启动前端开发服务器...');
    
    const frontend = spawn('npm', ['run', 'dev'], {
      cwd: __dirname,
      shell: true,
      stdio: 'inherit',
    });

    frontend.on('error', (err) => {
      log(colors.red, 'Frontend', `启动失败: ${err.message}`);
      process.exit(1);
    });

    frontend.on('close', (code) => {
      if (code !== 0 && code !== null) {
        log(colors.green, 'Frontend', `前端服务退出，代码: ${code}`);
      }
      process.exit(code || 0);
    });
  }, 2000);
}

// 主函数
function main() {
  console.log('\n' + colors.bright + colors.green + '🚀 启动 EvoCorps 开发环境...' + colors.reset + '\n');
  
  const backend = startBackend();
  startFrontend();

  // 处理退出信号
  process.on('SIGINT', () => {
    log(colors.yellow, 'System', '正在关闭服务...');
    backend.kill();
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    backend.kill();
    process.exit(0);
  });
}

main();
