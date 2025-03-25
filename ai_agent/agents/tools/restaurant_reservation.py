import os
from dotenv import load_dotenv
from datetime import date, time
from typing import Optional

from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool


load_dotenv()

db = SQLDatabase.from_uri(os.getenv("DATABASE_URL"))

@tool
def restaurant_reservation_tool(
    restaurant_id: int,
    restaurant_name: str,
    customer_name: str,
    customer_phone: str,
    reservation_date: date,
    reservation_time: time,
    number_of_people: int,
    special_requests: Optional[str] = None
) -> str:
    """
    創建新的訂位記錄
    
    Args:
        restaurant_id: 餐廳ID
        restaurant_name: 餐廳名稱
        customer_name: 顧客姓名
        customer_phone: 顧客電話
        reservation_date: 預訂日期 (YYYY-MM-DD)
        reservation_time: 預訂時間 (HH:MM)
        number_of_people: 用餐人數
        special_requests: 特殊要求（可選）
    """
    try:
        # 清理和驗證輸入數據
        restaurant_name = restaurant_name.replace("'", "''")  # 轉義單引號
        customer_name = customer_name.replace("'", "''")
        customer_phone = customer_phone.replace("'", "''")
        if special_requests:
            special_requests = special_requests.replace("'", "''")

        # 修改 SQL 查詢，使用 $1, $2 等參數佔位符
        query = f"""
        INSERT INTO reservations (
            restaurant_id, restaurant_name, customer_name, customer_phone,
            reservation_date, reservation_time, number_of_people,
            special_requests, status
        ) VALUES (
            {restaurant_id}, '{restaurant_name}', '{customer_name}', '{customer_phone}',
            '{reservation_date}', '{reservation_time}', {number_of_people},
            {'NULL' if special_requests is None else f"'{special_requests}'"}, 'pending'
        ) RETURNING id;
        """
        
        print('執行的 SQL 查詢:', query)  # 添加調試輸出
        result = db.run_no_throw(query)
        print('查詢結果:', result)  # 添加調試輸出
        
        if not result:
            return "訂位失敗：資料庫操作錯誤"
            
        return f"""
        訂位成功！
        餐廳：{restaurant_name}
        預訂人：{customer_name}
        電話：{customer_phone}
        日期：{reservation_date}
        時間：{reservation_time}
        人數：{number_of_people}
        特殊要求：{special_requests if special_requests else '無'}
        """
    except Exception as e:
        return f"訂位失敗：{str(e)}"
