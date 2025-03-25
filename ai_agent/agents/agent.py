# pylint: disable = http-used,print-used,no-self-use
import os
from typing import Annotated, TypedDict, Optional, List

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from pydantic import BaseModel, Field

from agents.prompt.prompt import *
from agents.tools.db_query import db_query_tool
from agents.tools.restaurant_reservation import restaurant_reservation_tool
from agents.tools.submit_final_answer import SubmitFinalAnswer
from agents.utils.utils import create_tool_node_with_fallback
from agents.utils.restaurant_parser import restaurant_parser

_ = load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

db = SQLDatabase.from_uri(DATABASE_URL)

class RestaurantInfo(BaseModel):
    """用於提取餐廳相關信息的結構化輸出模型"""
    food_type: Optional[str] = Field(None, description="食物類型或餐廳類型，例如：日本料理、火鍋、西餐等")
    budget: Optional[str] = Field(None, description="預算範圍，例如：100-200元、500元以下等")
    location: Optional[str] = Field(None, description="位置信息，例如：信義區、西門町等")
    time: Optional[str] = Field(None, description="用餐時間，例如：今晚7點、明天中午等")

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    #提供想吃什麼或是餐廳類型、預算、地點、時間
    food_type: Optional[str]
    budget: Optional[str]
    location: Optional[str]
    time: Optional[str]
    suggested_restaurant: Optional[str]  # 推薦的餐廳
    restaurant_recommendation_human_response: Optional[str]  # 餐廳推薦是否符合用戶需求
    suggested_restaurant_name: Optional[List[str]]  # 推薦的餐廳名稱
    suggested_restaurant_id: Optional[List[str]]  # 推薦的餐廳ID
    customer_name: Optional[str] = Field(None, description="用戶姓名")
    customer_phone: Optional[str] = Field(None, description="用戶電話")
    reservation_date: Optional[str] = Field(None, description="訂位日期")
    reservation_time: Optional[str] = Field(None, description="訂位時間")
    number_of_people: Optional[int] = Field(None, description="用餐人數")
    special_requests: Optional[str] = Field(None, description="特殊要求")

TOOLS = [db_query_tool]


class Agent:

    def __init__(self):
        toolkit = SQLDatabaseToolkit(db=db, llm=ChatOpenAI(model="gpt-4o"))
        tools = toolkit.get_tools()
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.restaurant_info_extractor = self.llm.with_structured_output(RestaurantInfo)
        self.restaurant_parser = restaurant_parser
        self.db_query_llm = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
            [db_query_tool], tool_choice="required"
        )
        self.restaurant_reservation_llm = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
            [restaurant_reservation_tool], tool_choice="required"
        )
        self.list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
        self.get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")
        self.get_schema_llm = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
            [self.get_schema_tool]
        )
        self.query_gen_llm =  ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(
            [SubmitFinalAnswer]
        )
        

        builder = StateGraph(AgentState)

        builder.add_node('restaurant_customer_service_agent_node', self.restaurant_customer_service_agent_node)
        builder.add_node('restaurant_recommendation_node', self.restaurant_recommendation_node)
        builder.add_node('restaurant_recommendation_human_check_node', self.restaurant_recommendation_human_check_node)
        builder.add_node("first_db_query_call", self.first_db_query_call)
        builder.add_node("list_tables_tool", create_tool_node_with_fallback([self.list_tables_tool]))
        builder.add_node("get_schema_tool", create_tool_node_with_fallback([self.get_schema_tool]))
        builder.add_node(
            "get_schema_llm",
            lambda state: {
                "messages": [self.get_schema_llm.invoke(state["messages"])],
            },
        )
        builder.add_node('query_gen_node', self.query_gen_node)
        builder.add_node("query_check_node", self.query_check_node)
        builder.add_node("execute_query_node", create_tool_node_with_fallback([db_query_tool]))
        builder.add_node("order_confirmation_node", self.order_confirmation_node)

        builder.set_entry_point("restaurant_customer_service_agent_node")
        
        builder.add_conditional_edges(
            'restaurant_customer_service_agent_node',
            self.restaurant_customer_service_agent_node_condition,
            {
                'restaurant_recommendation': 'restaurant_recommendation_node',
                'order_confirmation': 'order_confirmation_node',
                END: END
            }
        )
        
        builder.add_conditional_edges(
            'restaurant_recommendation_node',
            self.restaurant_recommendation_node_condition,
            {
                'order_confirmation': 'order_confirmation_node',
                'first_db_query_call': 'first_db_query_call'
            }
        )
        builder.add_edge("first_db_query_call", "list_tables_tool")
        builder.add_edge("list_tables_tool", "get_schema_llm")
        builder.add_edge("get_schema_llm", "get_schema_tool")
        builder.add_edge("get_schema_tool", "query_gen_node")
        builder.add_conditional_edges('query_gen_node', self.query_gen_node_condition, {'restaurant_recommendation_human_check': 'restaurant_recommendation_human_check_node', 'correct_query': 'query_check_node', 'query_gen': 'query_gen_node'})
        builder.add_edge("query_check_node", "execute_query_node")
        builder.add_edge("execute_query_node", "query_gen_node")
        builder.add_edge("restaurant_recommendation_human_check_node", "restaurant_recommendation_node")

        builder.add_edge('order_confirmation_node', END)
        memory = MemorySaver()
        self.graph = builder.compile(checkpointer=memory, interrupt_after=['restaurant_recommendation_human_check_node'])

        print(self.graph.get_graph().draw_mermaid())
        
    @staticmethod
    def query_gen_node_condition(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        # If there is a tool call, then we finish
        if isinstance(last_message, ToolMessage) and not last_message.content.startswith("Error:"):
            return 'restaurant_recommendation_human_check'
        if last_message.content.startswith("Error:"):
            return "query_gen"
        else:
            return "correct_query"
        
    @staticmethod
    def restaurant_customer_service_agent_node_condition(state: AgentState) -> str:
        """檢查是否已收集到所有必要資訊"""
        if all([
            state.get('food_type'),
            state.get('budget'),
            state.get('location'),
            state.get('time')
        ]):
            return 'restaurant_recommendation'
        return END
    
    @staticmethod
    def restaurant_recommendation_node_condition(state: AgentState) -> str:
        """檢查是否已收集到所有必要資訊"""
        if all([
            state.get('suggested_restaurant', ''),
            state.get('restaurant_recommendation_human_response', '') == '訂位'
        ]):
            return 'order_confirmation'
        return 'first_db_query_call'
    
    def restaurant_customer_service_agent_node(self, state: AgentState) -> AgentState:
        restaurant_info = {}
        last_message = state['messages'][-1]
        parse_message = [
            SystemMessage(content=parse_restaurant_info_prompt.format(last_message=last_message))
        ]
        
        # 使用结构化输出提取信息
        parsed_info = self.restaurant_info_extractor.invoke(parse_message)
        
        # 更新状态
        if parsed_info.food_type:
            restaurant_info['food_type'] = parsed_info.food_type
        if parsed_info.budget:
            restaurant_info['budget'] = parsed_info.budget
        if parsed_info.location:
            restaurant_info['location'] = parsed_info.location
        if parsed_info.time:
            restaurant_info['time'] = parsed_info.time

        # 检查哪些信息缺失
        missing_info = []
        info_mapping = {
            'food_type': '食物類型或餐廳類型',
            'budget': '預算',
            'location': '位置',
            'time': '用餐時間'
        }
        
        for key, display_name in info_mapping.items():
            if not restaurant_info.get(key):
                missing_info.append(display_name)
        
        response = ""
        # 如果有缺失信息，构建提示消息
        if missing_info:
            prompt_for_missing = f"""
            您好！為了給您提供更好的餐廳推薦，請告訴我以下資訊：
            {', '.join(missing_info)}
            
            目前的資訊：
            - 食物類型：{restaurant_info.get('food_type', '未提供')}
            - 預算：{restaurant_info.get('budget', '未提供')}
            - 位置：{restaurant_info.get('location', '未提供')}
            - 時間：{restaurant_info.get('time', '未提供')}
            """

            response = AIMessage(content=prompt_for_missing)
        

        return {
            "messages": [response],
            **restaurant_info,
        }
    
    
    def restaurant_recommendation_node(self, state: AgentState) -> AgentState:
        """基于收集到的資訊，生成餐廳推薦"""
        suggested_restaurant = state.get('suggested_restaurant', '')

        recommendation_context = f"""
        使用者偏好資訊：
        - 食物類型：{state.get('food_type', '未指定')}
        - 預算：{state.get('budget', '未指定')}
        - 位置：{state.get('location', '未指定')}
        - 時間：{state.get('time', '未指定')}
        
        請根據以上信息推薦合適的餐廳。對於每個推薦的餐廳，請提供：
        1. 餐廳名稱
        2. 位置
        3. 價格範圍
        4. 菜單所有品項
        5. 為什麼這家餐廳適合用戶
        
        推薦1家餐廳，並按照與用戶需求的匹配度排序。
        """
        response = HumanMessage(content=recommendation_context)

        if state.get('restaurant_recommendation_human_response', '') == "重新推薦":
            response = HumanMessage(content=recommendation_context + "之前推薦的推薦是" + suggested_restaurant + "請重新推薦")
            suggested_restaurant = ""
            
        return {
            "messages": [response],
            "suggested_restaurant": suggested_restaurant
        }

    def restaurant_recommendation_human_check_node(self, state: AgentState) -> AgentState:
        suggested_restaurant = state.get('suggested_restaurant', '')
        if suggested_restaurant:
            result = self.restaurant_parser.invoke({"suggested_restaurant": suggested_restaurant})
            # 因為只推薦一家餐廳，所以取第一個元素
            suggested_restaurant_name = result.restaurant_name if result.restaurant_name else ''
            suggested_restaurant_id = result.restaurant_id if result.restaurant_id else ''
            response = AIMessage(content=f"目前推薦的餐廳結果如下：\n\n{suggested_restaurant}\n\n請問用戶是否重新推薦？")
        else:
            response = AIMessage(content="目前沒有推薦的餐廳。")
            suggested_restaurant_name = ''
            suggested_restaurant_id = ''
        return {"messages": [response], "suggested_restaurant_name": suggested_restaurant_name, "suggested_restaurant_id": suggested_restaurant_id}

    
    def order_confirmation_node(self, state: AgentState) -> AgentState:
        """是否要訂位"""

        restaurant_name = state.get('suggested_restaurant_name', '')
        restaurant_id = state.get('suggested_restaurant_id', '')
        
        # 獲取訂位信息
        customer_name = state.get('customer_name', '')
        customer_phone = state.get('customer_phone', '')
        reservation_date = state.get('reservation_date', '')
        reservation_time = state.get('reservation_time', '')
        number_of_people = state.get('number_of_people', 0)
        special_requests = state.get('special_requests', '')

        # 準備 tool 的參數
        tool_args = {
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant_name,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "reservation_date": reservation_date,
            "reservation_time": reservation_time,
            "number_of_people": number_of_people,
            "special_requests": special_requests
        }
        
        print("準備執行訂位 tool，參數：", tool_args)
        
        try:
            # 直接調用 tool
            result = restaurant_reservation_tool.invoke(tool_args)
            return {"messages": [AIMessage(content=result)]}
        except Exception as e:
            error_message = f"訂位失敗：{str(e)}"
            return {"messages": [AIMessage(content=error_message)]}
        
    def first_db_query_call(self, state: AgentState) -> dict[str, list[AIMessage]]:
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "sql_db_list_tables",
                            "args": {},
                            "id": "tool_abcd123",
                        }
                    ],
                )
            ]
        }
    
    def query_check_node(self, state: AgentState) -> AgentState:
        message = [SystemMessage(content=query_check_prompt), HumanMessage(content=state['messages'][-1].content)]
        response = self.db_query_llm.invoke(message)
        return {"messages": [response]}
    
    def query_gen_node(self, state: AgentState) -> AgentState:
        suggested_restaurant = state.get('suggested_restaurant', "")
        message = state['messages']
        message = [SystemMessage(content=query_gen_prompt)] + message
        response = self.query_gen_llm.invoke(message)
        tool_messages = []
        if response.tool_calls:
            for tc in response.tool_calls:
                if tc["name"] == "SubmitFinalAnswer":
                    # 从 tool_calls 中获取 final_answer 并放入 content
                    final_answer = tc["args"].get("final_answer", "")
                    suggested_restaurant = final_answer
                    tool_messages.append(
                        ToolMessage(
                            content=final_answer,  # 直接使用 final_answer 作为 content
                            tool_call_id=tc["id"],
                        )
                    )
                else:
                    tool_messages.append(
                        ToolMessage(
                            content=f"Error: The wrong tool was called: {tc['name']}. Please fix your mistakes. Remember to only call SubmitFinalAnswer to submit the final answer. Generated queries should be outputted WITHOUT a tool call.",
                            tool_call_id=tc["id"],
                        )
                    )
        return {
            "messages": [response] + tool_messages, 
            "suggested_restaurant": suggested_restaurant
        }
