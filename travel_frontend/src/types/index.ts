// 类型定义

// 用户相关
export interface User {
  user_id: string
  email: string
  preferences?: string
  create_time: string
  update_time: string
}

// 登录响应
export interface LoginResponse {
  access_token: string
  token_type: string
}

// 行程相关
export interface Trip {
  trip_id: string
  user_id: string
  trip_name: string
  destination: string
  start_date: string
  end_date: string
  status: 'draft' | 'generated' | 'active' | 'completed'
  preferences?: string  // 行程偏好（可选）
  created_at: string
  updated_at: string
}

export interface TripListResponse {
  trips: Trip[]
}

// 行程详情
export interface HotelRecommendation {
  poi_id: string
  name: string
  reasoning: string
}

export interface TransportInfo {
  mode: string
  recommendation: string
  next_poi_id?: string
}

export interface Activity {
  poi_id: string | null
  poi_name: string
  activity_type: string
  latitude: number | null
  longitude: number | null
  estimated_time_slot: string
  estimated_duration_minutes: number
  notes?: string
  transport_to_next: TransportInfo | null
}

export interface TripDetail {
  detail_id: string
  trip_id: string
  day_number: number
  theme: string
  hotel_recommendation: HotelRecommendation
  activities: Activity[]
  map_url: string | null  // 该天的静态地图图片URL
  created_at: string
  updated_at: string
}

export interface BudgetCategory {
  name: string
  estimated_cny: number
}

export interface Budget {
  budget_id: string
  trip_id: string
  user_budget: number  // 用户准备的预算
  estimated_total: number  // LLM估算的总预算
  categories: BudgetCategory[]
  created_at: string
  updated_at: string
}

export interface TripDetailResponse {
  trip_header: Trip
  trip_details: TripDetail[]
  budget: Budget
}

// 费用相关
export interface Expense {
  expense_id: string
  trip_id: string
  category: string
  amount: number
  currency: string
  description: string
  timestamp: string
  created_at: string
}

export interface BudgetDetailResponse {
  budget: Budget
  expenses: Expense[]
  summary: {
    total_expense: number
    expense_by_category: Record<string, number>
    variance: {
      total: {
        estimated: number
        actual: number
        difference: number
        percentage: number
      }
      [category: string]: {
        estimated: number
        actual: number
        difference: number
        percentage: number
      }
    }
  }
}

