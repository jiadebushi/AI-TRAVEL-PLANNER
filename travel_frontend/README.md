# AI旅行规划师前端

基于 React + TypeScript + Vite 开发的AI旅行规划师前端应用。

## 项目结构

```
travel_frontend/
├── src/
│   ├── pages/              # 页面组件
│   │   ├── LoginPage.tsx   # 登录/注册页
│   │   ├── TripListPage.tsx # 行程列表页
│   │   ├── TripDetailPage.tsx # 行程详情页
│   │   └── ProfilePage.tsx # 个人主页
│   ├── components/         # 通用组件
│   │   ├── ExpenseModal.tsx # 开销录入弹窗
│   │   └── CreateTripModal.tsx # 创建行程弹窗
│   ├── routes/            # 路由配置
│   │   └── Router.tsx     # 路由定义
│   ├── api/               # API调用
│   │   ├── auth.ts        # 认证相关API
│   │   ├── trips.ts       # 行程相关API
│   │   ├── users.ts       # 用户相关API
│   │   └── budget.ts      # 费用管理API
│   ├── utils/             # 工具函数
│   │   └── api.ts         # axios配置
│   ├── types/             # TypeScript类型定义
│   │   └── index.ts
│   ├── App.tsx            # 根组件
│   ├── main.tsx           # 入口文件
│   └── index.css          # 全局样式
├── package.json
├── vite.config.ts
├── tsconfig.json
└── README.md
```

## 路由配置

- `/login` - 登录/注册页
- `/trips` - 行程列表页（主页）
- `/trips/:tripId` - 行程详情页
- `/profile` - 个人主页
- `/` - 重定向到 `/trips`

## 安装依赖

```bash
npm install
```

## 开发

```bash
npm run dev
```

## 构建

```bash
npm run build
```

## 预览构建结果

```bash
npm run preview
```

