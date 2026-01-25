# EvoCorps 前端

面向网络舆论去极化的进化式多智能体框架 - Web 管理界面

## 技术栈

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Tailwind CSS** - 样式框架
- **React Router** - 路由管理
- **Recharts** - 数据可视化
- **Lucide React** - 图标库
- **TanStack Query** - 数据请求管理

## 设计特点

- 🎨 **玻璃拟态设计** - 现代化的 Glassmorphism 风格
- 🌈 **蓝绿渐变配色** - 柔和的主题色彩
- ✨ **流畅动画** - 丝滑的交互体验
- 📱 **响应式布局** - 适配各种屏幕尺寸
- 🚀 **高性能** - 基于 Vite 的快速开发体验

## 功能模块

### 1. 主页
- 系统概览和关键指标
- 核心功能展示
- 系统状态监控

### 2. 服务管理
- 启动/停止/重启服务
- 服务状态监控
- 批量操作

### 3. 数据监控
- 实时情绪趋势
- 干预次数统计
- 实时警报系统

### 4. 实验管理
- 创建新实验
- 管理运行中的实验
- 查看实验进度和结果

### 5. 数据可视化
- 用户情绪分布
- 内容类型统计
- 干预效果对比
- 数据导出功能

### 6. 配置
- 基础参数配置
- 恶意机器人系统设置
- 舆论平衡系统设置
- API 密钥管理

## 快速开始

### 安装依赖

```bash
cd frontend
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 项目结构

```
frontend/
├── src/
│   ├── components/      # 公共组件
│   │   └── Layout.tsx   # 布局组件
│   ├── pages/           # 页面组件
│   │   ├── HomePage.tsx
│   │   ├── ServiceManagement.tsx
│   │   ├── DataMonitoring.tsx
│   │   ├── ExperimentManagement.tsx
│   │   ├── DataVisualization.tsx
│   │   └── ConfigPage.tsx
│   ├── App.tsx          # 应用入口
│   ├── main.tsx         # React 入口
│   └── index.css        # 全局样式
├── public/              # 静态资源
├── index.html           # HTML 模板
├── package.json         # 依赖配置
├── tsconfig.json        # TypeScript 配置
├── vite.config.ts       # Vite 配置
└── tailwind.config.js   # Tailwind 配置
```

## API 集成

前端通过 Vite 代理与后端通信：

```typescript
// 所有 /api/* 请求会被代理到 http://127.0.0.1:5000
axios.get('/api/health')
```

## 自定义配置

### 修改主题色

编辑 `tailwind.config.js` 中的 `colors.primary` 配置：

```javascript
colors: {
  primary: {
    500: '#14b8a6',  // 主色调
    // ...
  }
}
```

### 修改玻璃效果

编辑 `src/index.css` 中的 `.glass-card` 类：

```css
.glass-card {
  @apply bg-white/70 backdrop-blur-xl rounded-3xl shadow-glass;
}
```

## 浏览器支持

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

## 开发建议

1. 使用 TypeScript 确保类型安全
2. 遵循 React Hooks 最佳实践
3. 保持组件的单一职责
4. 使用 TanStack Query 管理服务端状态
5. 利用 Tailwind 的工具类快速开发

## License

MIT
