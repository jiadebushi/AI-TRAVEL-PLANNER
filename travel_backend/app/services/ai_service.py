"""AI 核心服务 - LLM 交互"""
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config import settings
from app.models.llm_models import UserIntent, ItineraryResponse, TripBudget, BudgetCategory
from app.models.api_models import TripInput
from typing import List, Dict, Any, Optional
import json


class AIService:
    """AI服务类，使用LangChain与千问LLM交互"""
    
    def __init__(self):
        # 使用LangChain的ChatOpenAI兼容接口调用千问API
        self.llm = ChatOpenAI(
            model="qwen-turbo",  # 或 "qwen-plus"
            temperature=0.7,
            openai_api_key=settings.qianwen_api_key,
            openai_api_base=settings.qianwen_api_base,
            max_tokens=4000
        )
    
    async def parse_user_intent(self, text: str) -> UserIntent:
        """解析用户意图，提取旅行要素"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的旅行规划助手。请从用户的输入文本中提取以下关键信息，并以JSON格式返回：
- destination: 目的地（字符串）
- start_date: 开始日期（ISO格式：YYYY-MM-DD）
- end_date: 结束日期（ISO格式：YYYY-MM-DD）
- budget_cny: 预算（人民币，浮点数，单位：元）
- people: 同行人数（字符串，如"2大1小"）
- preferences: 旅行偏好（字符串）

如果文本中没有明确提到某些信息，请根据上下文进行合理推断。"""),
            ("user", "{text}")
        ])
        
        parser = JsonOutputParser()
        prompt = prompt.partial(format_instructions=parser.get_format_instructions())
        
        chain = prompt | self.llm | parser
        
        result = await chain.ainvoke({"text": text})
        # 将JSON解析结果转换为Pydantic模型
        return UserIntent(**result)

    async def parse_trip_text(self, user_text: str) -> TripInput:
        """解析前端识别文本，提取 TripInput 字段"""
        parser = JsonOutputParser()

        # 使用普通字符串，避免 f-string 转义问题
        prompt_template = """
你是一个旅行助手，需要从用户的自然语言输入中提取关键信息并结构化输出。

请从用户输入的文本中提取以下字段：

- destination: str  — 目的地，例如 "东京" 或 "成都"
- start_date: date — 出发日期，格式为 YYYY-MM-DD；如果用户只提了"玩几天"，请设为明天的日期
- end_date: date — 结束日期，格式为 YYYY-MM-DD；如果用户只提了"玩几天"，请根据出发日期推算
- budget_cny: float — 预算（人民币），例如 3000；如果只说"大概花5000元"，取数字部分
- people: str — 出行人数及关系，例如 "2大1小"、"情侣"、"独自一人"
- preferences: str (可选) — 兴趣或偏好，例如 "喜欢美食和动漫"，没有可省略

请输出 JSON 格式结果，不要包含多余解释。

示例输入：
"我打算6月10号到6月15号和女朋友去东京玩，大概预算1万。"

示例输出：
{{
  "destination": "东京",
  "start_date": "2025-06-10",
  "end_date": "2025-06-15",
  "budget_cny": 10000,
  "people": "情侣",
  "preferences": null
}}

请严格仅输出一个合法 JSON 对象，不要输出任何解释或多余文字。

用户输入：
{user_text}
        """
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        # 先不走解析器，直接拿到模型原始文本，便于调试
        chain = prompt | self.llm
        llm_msg = await chain.ainvoke({"user_text": user_text})
        raw_text = getattr(llm_msg, "content", llm_msg)
        print(f"[voice-text] LLM raw text: {raw_text}")
        # 再尝试解析为JSON
        try:
            result = json.loads(raw_text)
        except Exception as e:
            print(f"[voice-text] JSON decode error: {e}")
            # 尝试用解析器做一次宽松解析
            try:
                result = parser.parse(raw_text)
            except Exception as e2:
                print(f"[voice-text] Parser failed: {e2}")
                raise ValueError("LLM 返回格式无法解析为 JSON")
        print(f"[voice-text] LLM parsed dict: {result}")

        # 规范化与容错
        destination = result.get("destination")
        start_date = result.get("start_date")
        end_date = result.get("end_date")
        budget_cny = result.get("budget_cny")
        people = result.get("people")
        preferences = result.get("preferences")

        # 可能出现空字符串/None，进行基本处理
        preferences = preferences or None

        # 容错：日期兜底
        try:
            from datetime import datetime, timedelta, date as date_cls
            sd: Optional[str] = start_date or None
            ed: Optional[str] = end_date or None
            if not sd:
                # 默认明天
                sd = (datetime.now().date() + timedelta(days=1)).isoformat()
            # 如果只有开始日期，且没有结束日期，则设为开始日期+1天
            if not ed:
                base = datetime.fromisoformat(sd).date()
                ed = (base + timedelta(days=1)).isoformat()
            start_date = sd
            end_date = ed
        except Exception as e:
            print(f"[voice-text] date fallback error: {e}")
            from datetime import datetime, timedelta
            sd = (datetime.now().date() + timedelta(days=1)).isoformat()
            ed = (datetime.now().date() + timedelta(days=2)).isoformat()
            start_date = sd
            end_date = ed

        return TripInput(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            budget_cny=float(budget_cny) if budget_cny is not None else 0.0,
            people=people or "",
            preferences=preferences
        )
    
    async def llm_plan_decision(self, user_data: Dict[str, Any], poi_list: List[Dict[str, Any]]) -> ItineraryResponse:
        """LLM决策行程规划和交通方式"""
        # 构建prompt（参考prompt_example.md）
        poi_json = json.dumps(poi_list, ensure_ascii=False, indent=2)
        
        prompt_template = """**角色与任务:**
你是一位专业的旅行规划师AI。你的任务是根据用户提供的旅行需求和已检索到的地理位置数据（POI列表），生成一个详细、个性化的每日旅行路线。

**核心要求:**
1. **完整性:** 必须覆盖用户的所有旅行天数。
2. **合理性:** 每日行程安排必须考虑**地理位置的临近性**和**用户偏好**。
3. **交通决策:** 必须为**每个活动之间**的移动推荐最佳的交通方式（步行、地铁、公交、打车/私家车），并注明推荐理由。这**包括**从景点到餐厅，以及从餐厅到下一个景点的交通。
4. **游览时间 :** 必须为活动分配合理的 `estimated_time_slot`。
   - **大型主题公园** (如迪士尼、环球影城)：必须分配**一整天** (例如 09:00 - 20:00)。
   - **大型博物馆/动物园** (如故宫、上野动物园)：必须分配**至少半天** (4-5 小时)，且其有固定开放时间，游览时间必须严格安排在 09:00 - 18:00 之间。
   - **普通景点/商圈**：分配 1-3 小时。
   - 夜景 (如观景台)：必须安排在晚上 (例如 19:00 之后)，但不得晚于 22:00。
5. **酒店推荐:** 必须根据用户预算和行程，在每天的 `hotel_recommendation` 字段中推荐一个酒店。
   * **关键逻辑:** 如果用户在**同一个城市**，**每天的酒店推荐必须保持一致**（使用同一个 `poi_id`）。只在跨城市旅行时更换酒店。
   * 优先选择**传统的、知名的连锁酒店** (例如：希尔顿、万豪、洲际、假日酒店、华住会等)。
6. **餐饮推荐与灵活性:** 必须为早、中、晚三餐提供餐饮建议。
   * **餐饮推荐应多样化，避免重复**，并优先**体现当地美食特色**。
   * 餐饮的 `estimated_time_slot` 必须位于时间窗口之内：早餐 07:00-09:00；午餐 11:00-14:00；晚餐 17:00-20:00。
   * 可从`POI_List` 中列表选择一个**具体的餐厅**，或推荐一个**地理位置合理的商圈/美食街**，此时 `poi_id` 设为 `null`，`poi_name` 为商圈名。
7. **预算：**根据用户的预算，你给出的总的预算必须控制在用户的预算的60\%-85\%之间。
8. **严格的 JSON 格式:** 最终输出必须是一个遵循下方 Schema 定义的**纯 JSON 字符串**，不允许包含任何额外的解释性文本。

**用户需求 (User_Input):**
* **目的地:** {destination}
* **天数:** {days}天
* **预算 (元):** {budget_cny}
* **同行人数:** {people}
* **偏好:** {preferences}

**地理位置资源 (POI_List):**
你已经通过地图 API 检索了以下POI，请从中进行选择和排序，生成最终路线。
{poi_list}

**输出格式要求:**
请严格按照以下JSON格式输出，不要添加任何额外文本：
{{
  "trip_name": "生成的行程名称",
  "daily_plans": [
    {{
      "day": 1,
      "theme": "第一日主题",
      "hotel_recommendation": {{
        "poi_id": "H001 或 null",
        "name": "酒店名称或null",
        "reasoning": "推荐理由"
      }},
      "activities": [
        {{
          "poi_id": "POI的ID或null",
          "poi_name": "POI名称或商圈名",
          "activity_type": "Meal_Breakfast|Meal_Lunch|Meal_Dinner|Attraction|...",
          "latitude": 纬度,
          "longitude": 经度,
          "estimated_time_slot": "时间段，如：9:00-12:00",
          "estimated_duration_minutes": 预估停留分钟数,
          "notes": "活动说明和建议",
          "transport_to_next": {{
            "mode": "交通方式",
            "recommendation": "推荐理由",
            "next_poi_id": "下一个POI的ID或null"
          }}
        }}
      ]
    }}
  ]
}}
"""
        
        # 计算天数
        from datetime import datetime
        start_date = datetime.fromisoformat(user_data["start_date"])
        end_date = datetime.fromisoformat(user_data["end_date"])
        days = (end_date - start_date).days + 1
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        parser = JsonOutputParser()
        prompt = prompt.partial(format_instructions=parser.get_format_instructions())
        
        chain = prompt | self.llm | parser
        
        result = await chain.ainvoke({
            "destination": user_data["destination"],
            "days": days,
            "budget_cny": user_data["budget_cny"],
            "people": user_data["people"],
            "preferences": user_data["preferences"],
            "poi_list": poi_json
        })
        
        return ItineraryResponse(**result)
    
    async def estimate_budget(self, trip_details: Dict[str, Any], user_data: Dict[str, Any], user_budget: float) -> TripBudget:
        """估算行程预算"""
        prompt_template = """作为专业的旅行预算规划师，请根据以下信息估算详细的旅行预算：

**行程信息:**
- 目的地: {destination}
- 天数: {days}天
- 同行人数: {people}
- 用户偏好: {preferences}
- 用户准备的预算: {user_budget}元

**详细行程:**
{trip_details}

**重要约束:**
7. **预算控制:** 根据用户的预算，你给出的总预算 (`estimated_total_cny`) 必须控制在用户预算的 **70% - 85%** 之间。即：
   - 最低预算 = 用户预算 × 0.60
   - 最高预算 = 用户预算 × 0.85
   - 你估算的总预算必须落在此区间内

请估算总预算和各项开支的细分（住宿、餐饮、交通、门票、购物等），并以JSON格式返回。

输出格式：
{{
  "estimated_total_cny": 总预算（元，必须在用户预算的60%-85%之间）,
  "categories": [
    {{"name": "住宿", "estimated_cny": 金额}},
    {{"name": "餐饮", "estimated_cny": 金额}},
    {{"name": "交通", "estimated_cny": 金额}},
    {{"name": "门票", "estimated_cny": 金额}},
    ...
  ]
}}
"""
        
        from datetime import datetime
        start_date = datetime.fromisoformat(user_data["start_date"])
        end_date = datetime.fromisoformat(user_data["end_date"])
        days = (end_date - start_date).days + 1
        
        trip_details_json = json.dumps(trip_details, ensure_ascii=False, indent=2)
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        parser = JsonOutputParser()
        prompt = prompt.partial(format_instructions=parser.get_format_instructions())
        
        chain = prompt | self.llm | parser
        
        result = await chain.ainvoke({
            "destination": user_data["destination"],
            "days": days,
            "people": user_data["people"],
            "preferences": user_data["preferences"],
            "user_budget": user_budget,
            "trip_details": trip_details_json
        })
        
        # 验证预算是否在合理范围内（60%-85%）
        min_budget = user_budget * 0.60
        max_budget = user_budget * 0.85
        estimated = result["estimated_total_cny"]
        
        # 如果超出范围，自动调整到范围内
        if estimated < min_budget:
            result["estimated_total_cny"] = min_budget
        elif estimated > max_budget:
            result["estimated_total_cny"] = max_budget
        
        # 转换为TripBudget对象
        return TripBudget(
            trip_id="",  # 将在service层设置
            estimated_total_cny=result["estimated_total_cny"],
            categories=[BudgetCategory(**cat) for cat in result["categories"]]
        )

    async def extract_poi_keywords(self, preference_text: str) -> List[str]:
        """根据偏好文本提取用于地图POI检索的核心关键词列表。
        参照 prompt_poikeyworks.md 规则：
        - 理解语义；
        - 每个类别仅提取1-2个最核心关键词；
        - 仅返回JSON数组字符串。
        """
        prompt_template = (
            "你是一个旅行偏好分析助手。请从用户的偏好描述中，智能提取出最核心、适合用于地图 POI 搜索的关键词列表。\n"
            "要求：\n"
            "1) 理解语义（如‘二次元圣地’提取‘动漫’）。\n"
            "2) 每个识别出的偏好类别，只提取1-2个最核心关键词。\n"
            "3) 只返回一个 JSON 字符串列表（JSON array of strings），不要包含任何其他解释性文字。\n\n"
            "用户偏好: {preference_text}\n输出："
        )
        prompt = ChatPromptTemplate.from_template(prompt_template)
        parser = JsonOutputParser()
        prompt = prompt.partial(format_instructions=parser.get_format_instructions())
        chain = prompt | self.llm | parser
        try:
            result = await chain.ainvoke({"preference_text": preference_text})
            if isinstance(result, list):
                return [str(x) for x in result if isinstance(x, (str, int, float))][:10]
            return []
        except Exception:
            return []
    
    async def parse_expense_text(self, text: str) -> Dict[str, Any]:
        """解析开销文本，提取结构化信息"""
        prompt_template = """请从用户的文本输入中提取开销信息，返回JSON格式：

输入文本: {text}

请提取以下信息：
- category: 开销类别（如：餐饮、交通、住宿、门票、购物等）
- amount: 金额（浮点数）
- currency: 货币单位（默认CNY）
- description: 描述（字符串）

输出JSON格式：
{{
  "category": "类别",
  "amount": 金额,
  "currency": "CNY",
  "description": "描述"
}}

如果无法提取完整信息，请尽可能推断并标注。
"""
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        parser = JsonOutputParser()
        prompt = prompt.partial(format_instructions=parser.get_format_instructions())
        
        chain = prompt | self.llm | parser
        
        result = await chain.ainvoke({"text": text})
        return result


# 全局AI服务实例
ai_service = AIService()

