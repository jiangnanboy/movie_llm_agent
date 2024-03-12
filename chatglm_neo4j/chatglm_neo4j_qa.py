from typing import Optional
from langchain_community.llms import ChatGLM
from chatglm_neo4j.utils import get_candidates, get_candidates2, fulltext_search_query_get_entity

chatglm_server_url = "http://192.168.0.200:5000/chat"

llm = ChatGLM(endpoint_url=chatglm_server_url,
              max_token=8000,
              #history=[['']],
              top_p=0.9,
              model_kwargs={"sample_model_args": False})

from typing import List, Tuple, Any, Union
from langchain.schema import AgentAction, AgentFinish
from langchain.agents import BaseSingleActionAgent
from langchain import LLMChain, PromptTemplate
from langchain.base_language import BaseLanguageModel


class IntentAgent(BaseSingleActionAgent):
    tools: List
    llm: BaseLanguageModel
    intent_template: str = """
    现在有一些意图，类别为{intents}，你的任务是理解用户问题的意图，并判断该问题属于哪一类意图。
    回复的意图类别必须在提供的类别中，并且必须按格式回复：“意图类别：<>”。

    举例：
    问题：周星驰主演的电影有哪些？
    意图类别：person_qa_movie
    
    问题：吴孟达参演了什么电影？
    意图类别：person_qa_movie

    问题：我想看喜剧类电影？
    意图类别：recom_qa_movie
    
    问题：我喜欢看剧情类电影？
    意图类别：recom_qa_movie
    
    问题：我想看剧情类的电影？
    意图类别：recom_qa_movie
    
    问题：“{query}”
    """
    prompt = PromptTemplate.from_template(intent_template)
    llm_chain: LLMChain = None

    def get_llm_chain(self):
        if not self.llm_chain:
            self.llm_chain = LLMChain(llm=self.llm, prompt=self.prompt)
    def choose_tools(self, query) -> List[str]:
        self.get_llm_chain()
        tool_names = [tool.name for tool in self.tools]
        resp = self.llm_chain.predict(intents=tool_names, query=query)
        select_tools = [(name, resp.index(name)) for name in tool_names if name in resp]
        select_tools.sort(key=lambda x: x[1])
        return [x[0] for x in select_tools]

    @property
    def input_keys(self):
        return ["input"]

    def plan(
            self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[AgentAction, AgentFinish]:
        # only for single tool
        tool_name = self.choose_tools(kwargs["input"])[0]
        print('意图是:{}'.format(tool_name))

        return AgentAction(tool=tool_name, tool_input=kwargs["input"], log="")

    async def aplan(
            self, intermediate_steps: List[Tuple[AgentAction, str]], **kwargs: Any
    ) -> Union[List[AgentAction], AgentFinish]:
        raise NotImplementedError("IntentAgent does not support async")


from langchain.tools import BaseTool
from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)

class functional_Tool(BaseTool):
    name: str = ""
    description: str = ""
    url: str = ""

    def _call_func(self, query):
        raise NotImplementedError("subclass needs to overwrite this method")

    def _run(
            self,
            query: str,
            run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        return self._call_func(query)

    async def _arun(
            self,
            query: str,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        raise NotImplementedError("APITool does not support async")

def get_person_movie(name: str):
    candidates = get_candidates(name)
    if not candidates:
        return "数据库中没有找到相关人物的电影"
    return candidates

class Person_Tool(functional_Tool):
    llm: BaseLanguageModel
    # tool description
    name = "person_qa_movie"
    description = "当你需要回答关于明星主演或参演了哪些电影时很有用"
    qa_template = """
        抽取下面问题中的实体和对应的实体类型。
        问题：{query}
        """
    prompt = PromptTemplate.from_template(qa_template)
    llm_chain: LLMChain = None

    def _call_func(self, query) -> str:
        self.get_llm_chain()
        resp = self.llm_chain.predict(query=query)
        entity_type = resp.strip().split('\n')
        entity = ''
        type = ''
        for item in entity_type:
            if (item[:3] == '实体：') or (item[:3] == '实体:'):
                entity = item[3:]
            if (item[:5] == '实体类型：') or (item[:5] == '实体类型:'):
                type = item[5:]
        info = ''
        if (entity != '') and (type != ''):
            if type in ['人物', '演员', '明星']:
                info = get_person_movie(entity)
        if info == '':
            search_entity = fulltext_search_query_get_entity(query, 'person')
            for ent in search_entity:
                entity = ent[0]
                break
            if entity != '':
                info = get_person_movie(entity)

        return info

    def get_llm_chain(self):
        if not self.llm_chain:
            self.llm_chain = LLMChain(llm=self.llm, prompt=self.prompt)

def get_genre_movie(name: str):
    candidates = get_candidates2(name)
    if not candidates:
        return "数据库中没有找到相关类型的电影"
    return candidates

class Genre_Tool(functional_Tool):
    llm: BaseLanguageModel
    # tool description
    name = "recom_qa_movie"
    description = "当你想看某种类型、某种体裁或某种类别的电影时很有用"
    qa_template = """
           抽取下面问题中的电影类别或体裁。
           问题：{query}
           """
    prompt = PromptTemplate.from_template(qa_template)
    llm_chain: LLMChain = None
    def _call_func(self, query) -> str:
        self.get_llm_chain()
        resp = self.llm_chain.predict(query=query)
        all_genres = [
            '喜剧',
            '奇幻',
            '冒险',
            '剧情',
            '爱情',
            '古装',
            '家庭'
        ]
        movie_genre = ''
        for genre in all_genres:
            if genre in resp:
                movie_genre = genre
                break
        if movie_genre !='':
            info = get_genre_movie(movie_genre)
            return info

    def get_llm_chain(self):
        if not self.llm_chain:
            self.llm_chain = LLMChain(llm=self.llm, prompt=self.prompt)

from langchain.agents import AgentExecutor

tools = [Person_Tool(llm=llm), Genre_Tool(llm=llm)]

agent = IntentAgent(tools=tools, llm=llm)
agent_exec = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, verbose=True, max_iterations=1)


result = agent_exec.invoke({"input":"李丽珍参演的电影"})
'''
意图是:person_qa_movie
['家有喜事']
'''
# result = agent_exec.invoke({"input":"我想看剧情类的电影"})
'''
意图是:recom_qa_movie
['家有喜事', '算死草', '行运一条龙', '新喜剧之王']
'''
print(result.values())
