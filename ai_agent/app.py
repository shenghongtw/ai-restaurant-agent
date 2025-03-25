# pylint: disable = invalid-name
import os
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

from agents.agent import Agent


def initialize_agent():
    if 'agent' not in st.session_state:
        st.session_state.agent = Agent()


def render_custom_css():
    st.markdown(
        '''
        <style>
        .main-title {
            font-size: 2.5em;
            color: white;
            text-align: center;
            margin-bottom: 0.5em;
            font-weight: bold;
        }
        .sub-title {
            font-size: 1.2em;
            color: white;
            text-align: left;
            margin-bottom: 0.5em;
        }
        .center-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
        }
        .query-box {
            width: 80%;
            max-width: 600px;
            margin-top: 0.5em;
            margin-bottom: 1em;
        }
        .query-container {
            width: 80%;
            max-width: 600px;
            margin: 0 auto;
        }
        </style>
        ''', unsafe_allow_html=True)

def render_order_or_rerecommendation_form():
    st.subheader('請選擇')
    config = {'configurable': {'thread_id': st.session_state.thread_id}}
    if st.button('重新推薦', key='recommend_again_button'):
        result = st.session_state.agent.graph.invoke({'restaurant_recommendation_human_response': '重新推薦'}, config=config)
        response_content = result['messages'][-1].content
        st.subheader('餐廳資訊')
        st.write(response_content)
        
    if st.button('訂位', key='reservation_button'):
        # 設置狀態表示要顯示訂位表單
        st.session_state.show_reservation_form = True
        st.rerun()  # 立即重新運行頁面

def render_restaurant_order_form():
    if not st.session_state.get('show_reservation_form', False):
        return

    config = {'configurable': {'thread_id': st.session_state.thread_id}}
    
    # 添加一個返回按鈕
    if st.button('返回', key='back_button'):
        st.session_state.show_reservation_form = False
        st.rerun()
        
    with st.form(key='reservation_form'):
        st.subheader('請輸入訂位資訊')
        restaurant_name = st.session_state.get('suggested_restaurant_name', '')
        st.info(f'餐廳名稱：{restaurant_name}')
        restaurant_recommendation_human_response = '訂位'
        customer_name = st.text_input('姓名', key='name_input')
        customer_phone = st.text_input('電話', key='phone_input')
        reservation_date = st.date_input('日期', key='date_input')
        reservation_time = st.time_input('時間', key='time_input')
        number_of_people = st.number_input('人數', min_value=1, key='people_input')
        special_requests = st.text_area('特殊要求', key='requests_input')
        
        submit_button = st.form_submit_button('確認訂位')
        
        if submit_button:
            print("表單已提交") # 用於調試
            try:
                input_data = {
                    'suggested_restaurant': st.session_state.get('suggested_restaurant', ''),
                    'restaurant_recommendation_human_response': restaurant_recommendation_human_response,
                    'customer_name': customer_name,
                    'customer_phone': customer_phone,
                    'reservation_date': str(reservation_date),
                    'reservation_time': str(reservation_time),
                    'number_of_people': number_of_people,
                    'special_requests': special_requests
                }
                
                print("輸入數據:", input_data) # 用於調試
                
                result = st.session_state.agent.graph.invoke(input_data, config=config)
                print('result', result)
                if result and 'messages' in result:
                    response_content = result['messages'][-1].content
                    st.subheader('訂位結果')
                    st.write(response_content)
                    # 訂位完成後重置表單狀態
                    st.session_state.show_reservation_form = False
                else:
                    st.error('未收到有效的訂位結果')
                    
            except Exception as e:
                st.error(f"處理訂位時發生錯誤: {str(e)}")
                print(f"訂位錯誤: {str(e)}")

def render_ui():
    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">✈️🌍 AI 餐廳推薦 🏨🗺️</div>', unsafe_allow_html=True)
    st.markdown('<div class="query-container">', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">請提供想吃什麼或是餐廳類型、預算、地點、時間, 例如: 滷肉飯、 預算不限, 台北,時間不限</div>', unsafe_allow_html=True)
    user_input = st.text_area(
        '餐廳查詢',
        height=200,
        key='query',
        placeholder='請輸入餐廳查詢',
    )
    st.markdown('</div>', unsafe_allow_html=True)
    st.sidebar.image('images/ai-restaurant.png', caption='AI 餐廳推薦')

    return user_input


def process_query(user_input):
    if user_input:
        try:
            if 'thread_id' not in st.session_state:
                thread_id = str(uuid.uuid4())
                st.session_state.thread_id = thread_id
            else:
                thread_id = st.session_state.thread_id
            messages = [HumanMessage(content=user_input)]
            config = {'configurable': {'thread_id': thread_id}}

            result = st.session_state.agent.graph.invoke({'messages': messages}, config=config)
            response_content = result['messages'][-1].content
            st.subheader('餐廳資訊')
            st.write(response_content)

            if 'suggested_restaurant' in result:
                suggested_restaurant = result['suggested_restaurant']
                suggested_restaurant_name = result['suggested_restaurant_name']
                st.session_state.suggested_restaurant = suggested_restaurant
                st.session_state.suggested_restaurant_name = suggested_restaurant_name

            # if 'order_or_not' in result:
            #     order_or_not = result['order_or_not']
            #     st.session_state.order_or_not = order_or_not

        except Exception as e:
            st.error(f'Error: {e}')
    else:
        st.error('Please enter a restaurant query.')

def main():
    initialize_agent()
    render_custom_css()
    user_input = render_ui()

    if st.button('取得餐廳資訊'):
        process_query(user_input)
    if 'suggested_restaurant' in st.session_state:
        # 只有當不顯示訂位表單時才顯示選擇按鈕
        if not st.session_state.get('show_reservation_form', False):
            render_order_or_rerecommendation_form()
        else:
            render_restaurant_order_form()
    # if 'order_or_not' in st.session_state:
    #     render_restaurant_order_form()

if __name__ == '__main__':
    main()
