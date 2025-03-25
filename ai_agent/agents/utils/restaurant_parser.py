from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

class Restaurant(BaseModel):
    """Restaurant information extracted from suggestions."""
    restaurant_name: str = Field(..., description="餐廳名稱")
    restaurant_id: str = Field(..., description="餐廳ID")

# LLM with function call
llm = ChatOpenAI(model="gpt-4o", temperature=0)
structured_restaurant_parser = llm.with_structured_output(Restaurant)

# Create prompt template
restaurant_parser_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一個資訊提取助手。請從提供的文字中提取餐廳的完整名稱和ID資訊。
特別注意：
1. 餐廳名稱通常出現在"餐廳名稱:"後面，請提取完整的名稱
2. 如果看到類似"XX提供..."的句子中出現的餐廳名稱，這也是完整名稱的來源
3. 請確保提取的是完整的餐廳名稱，而不是部分名稱

例如：
輸入文字中如果出現：
餐廳名稱: 大麥
...
大麥提供美味的滷肉飯

應該提取的餐廳名稱是"大麥"而不是"大"
"""),
    ("human", "{suggested_restaurant}")
])

restaurant_parser = restaurant_parser_prompt | structured_restaurant_parser