// 公开路由组件，如果已登录则重定向到首页

import { Navigate } from 'react-router-dom'

interface PublicRouteProps {
  children: React.ReactNode
}

function PublicRoute({ children }: PublicRouteProps) {
  const token = localStorage.getItem('access_token')
  
  if (token) {
    return <Navigate to="/trips" replace />
  }
  
  return <>{children}</>
}

export default PublicRoute

