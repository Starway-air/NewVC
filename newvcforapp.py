import os
import re
import sys
from typing import Sequence
from datetime import datetime
import time
from tavily import TavilyClient
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel,Field
from langchain.tools import  tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.globals import set_verbose
from compile import compile,simulate
from RAG import RAG
from Models import Models
from concurrent.futures import ThreadPoolExecutor
# 确保环境变量优先使用UTF-8
os.environ["PYTHONIOENCODING"] = "utf-8"
# 强制设置标准输出流为UTF-8编码
"""if sys.stdout.encoding != 'UTF-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, 
                                encoding='utf-8',
                                errors='replace',
                                line_buffering=True)"""
set_verbose(True)
# 如果是Windows系统，额外设置控制台代码页
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')  # 设置为UTF-8代码页

#代码文件自定义处：
apikey=''
Tavilykey=""
MAXITEMS=9


class Newvc():

    def anounce(self):
        anouncement=r"""
     __                             ___ 
  /\ \ \  ___ __      __ /\   /\   / __\
 /  \/ / / _ \\ \ /\ / / \ \ / /  / /   
/ /\  / |  __/ \ V  V /   \ V /  / /___ 
\_\ \/   \___|  \_/\_/     \_/   \____/ 
                                        
"""
        anouncement1=r"""
███╗   ██╗███████╗██╗    ██╗██╗   ██╗ ██████╗
████╗  ██║██╔════╝██║    ██║██║   ██║██╔════╝
██╔██╗ ██║█████╗  ██║ █╗ ██║██║   ██║██║     
██║╚██╗██║██╔══╝  ██║███╗██║╚██╗ ██╔╝██║     
██║ ╚████║███████╗╚███╔███╔╝ ╚████╔╝ ╚██████╗
╚═╝  ╚═══╝╚══════╝ ╚══╝╚══╝   ╚═══╝   ╚═════╝

"""
        b='正在使用的是中国东南大学2025届学生毕业设计成果\n这是由LLM驱动的Verilog与c++代码自动生成及处理系统\n有关本软件更多信息,联系邮箱:213210411@seu.edu.cn'
        print(self.colored_text(anouncement1,32,49,1))
        print(self.colored_text(b,32,49,1))
        time.sleep(2)
    #提取特定代码块
    def extract(self,msg:str,kw:str=''):
        if kw in msg:
            match = re.search(rf"```{kw}\n(.*?)```",msg, flags=re.DOTALL)
            if match:
                extractmsg = match.group(1)
                return extractmsg.strip()
            else:
                self.printc(f'没有匹配到{kw}代码块,extract失败')
                raise ValueError(f"没有匹配到{kw}代码块,extract失败")
        else:
            raise ValueError(f"没有匹配到{kw},extract失败")

    #记录输出
    def savelog(self,msg):
        with open(os.path.join(self.dir,'runtemp',"logmsg.md"),"a+",encoding="utf-8") as f:
            f.write(f"\n{msg}\n")

    #将代码保存在runtemp/codetemp下的文件中，便于后续读取
    def savecode(self,code:str,name:str,dir:str=''):
        """保存代码"""
        if dir:
            codedir=dir
        else:
            codedir=os.path.join(self.dir,'runtemp','codetemp')
        with open(os.path.join(codedir,name),"w+",encoding="utf-8") as f:
            f.write(code)
            self.printc(f"代码保存成功，文件名为{name},位置:{codedir}")
        
    def read_all(self,file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            content = "".join(file.readlines()).strip()
            return content
        
    def __init__(self,apikey:str=None,modelname:str=None,modeltype:str=None,Tavilykey:str=None,maxitems:int=8,TYPE:str="verilog",maxsearch:int=3,llmdict:dict=None,addmodel:dict=None,init_after=False):
         #获取当前脚本所在目录
        self.dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        #创建运行数据存储文件夹
        def make_dir(dir):
            if not os.path.exists(dir):
                os.makedirs(dir)
        make_dir(os.path.join(self.dir,"runtemp","compiletemp"))#编译仿真产生的临时文件
        make_dir(os.path.join(self.dir,"runtemp","codetemp"))#代码生成的临时文件
        make_dir(os.path.join(self.dir,"runtemp","finalcode"))
        if init_after:
            return
        self.modelname=modelname
        self.Tavilykey=Tavilykey
        self.MAXITEMS=maxitems
        self.TYPE=TYPE
        self.maxsearch=maxsearch#搜索最大次数

        self.count=0
        self.fixcount=0

        #参数初始化
        self.QUESTION=""
        self.MODULE=""
        self.TESTBENCH=""
        self.CODE=""
        self.taskname=''
        self.testbenchlc=''
        self.reflc=''
        self.testbench_generate_need=True
        #统计参数初始化
        self.all=0
        self.lose=0
        self.result=False
        self.one_shot=True
       
        self.memory=MemorySaver()
        self.llm=Models()
        #模型设置初始化
        if addmodel:
            self.llm.add(addmodel)
        self.llm.set(api_key=apikey,modeltype=modeltype)
        
        self.modelinit(llmdict)

        #self.agent = create_react_agent(self.reactllm, tools=self.tools(),checkpointer=self.memory, prompt=self.identity)
    
    def update(self,apikey,modelname:str=None,modeltype:str=None,Tavilykey:str=None,maxitems:int=8,TYPE:str="verilog",maxsearch:int=3,llmdict:dict=None,addmodel:dict=None):
        self.modelname=modelname
        self.Tavilykey=Tavilykey
        self.MAXITEMS=maxitems
        self.TYPE=TYPE
        self.maxsearch=maxsearch#搜索最大次数

        self.count=0
        self.fixcount=0

        #参数初始化
        self.QUESTION=""
        self.MODULE=""
        self.TESTBENCH=""
        self.CODE=""
        self.taskname=''
        self.testbenchlc=''
        self.reflc=''
        self.testbench_generate_need=True
        #统计参数初始化
        self.all=0
        self.lose=0
        self.result=False
        self.one_shot=True

        self.memory=MemorySaver()
        self.fixmemory=InMemoryChatMessageHistory(session_id="fix-session")
        self.llm=Models()
        #模型设置初始化
        if addmodel:
            self.llm.add(addmodel)
        self.llm.set(api_key=apikey,modeltype=modeltype)
        
        self.modelinit(llmdict)
    
    #具有辨别性的区分
    def colored_text(self,text,color_code,background_code=None,style_code=None):
        if background_code is not None and style_code is not None:
            return f"\033[{style_code};{color_code};{background_code}m{text}\033[0m"
        elif background_code is not None:
            return f"\033[{color_code};{background_code}m{text}\033[0m"
        elif style_code is not None:
            return f"\033[{style_code};{color_code}m{text}\033[0m"
        else:
            return f"\033[{color_code}m{text}\033[0m"
    def printc(self,msg:str,color:int=36,back=None,style=None,end=None):
        xyz=self.colored_text(text=msg,color_code=color,background_code=back,style_code=style)
        if end!=None:
            print(xyz,end=end)
        else:print(xyz)
    #coverage_rigor:覆盖严格度，即比较修正前后代码质量评分的差值要求，差值越小，修正质量要求越高，默认为100即关闭评分比较，直接覆盖
    def run(self,messages:str="",question:str="",module:str="",thread_id:str="1",newmemory:bool=False,TYPE:str="",maxitems:int=None,taskname:str=None,testbenchcode:str='',testbenchlc:str='',coverage_rigor:int=100,recursion_limit:int=100,reflc:str=''):    
        printc=self.printc

        if newmemory:
            self.cleantemp()
            self.memory=MemorySaver()
        if testbenchcode or testbenchlc:
            self.testbench_generate_need=False

        agent=self.newvcagent(coverage_rigor=coverage_rigor,TYPE=TYPE,maxitems=maxitems)

        if testbenchcode:
            self.TESTBENCH=testbenchcode
            printc(f"已从输入写入testbench")
        elif testbenchlc:
            self.testbenchlc=testbenchlc
            self.TESTBENCH=self.read_all(testbenchlc)
            printc(f"\n已从{self.testbenchlc}写入testbench\n")

        if maxitems:
            self.MAXITEMS=maxitems

        if taskname:
            self.taskname=taskname
        if reflc:
            self.reflc=reflc
        #清理同时记录
        def clean(msg):
            with open(os.path.join(self.dir,'runtemp',"logmsg.md"),"a+",encoding="utf-8") as f:
                f.write(f"\n{msg}\n")
            if ('```verilog') in msg:
                match = re.search(r"```verilog\n(.*?)```",msg, flags=re.DOTALL)
                if match:
                    cleanmsg = match.group(1)
                    return cleanmsg
                else:
                    printc('没有匹配到Verilog代码块,clean无效')
                    return msg
            elif '```cpp' in msg or '```c++' in msg:
                match = re.search(r"```(cpp|c\+\+)\n(.*?)```",msg, flags=re.DOTALL)
                if match:
                    cleanmsg = match.group(2)
                    return cleanmsg
                else:
                    printc('没有匹配到C++代码块,clean无效')
                    return msg
            elif ('```text') in msg:
                match = re.search(r"```text\n(.*?)```",msg, flags=re.DOTALL)
                if match:
                    cleanmsg = match.group(1)
                    return cleanmsg
                else:
                    printc('没有匹配到text代码块,clean无效')
                    return msg
            else:
                printc('输出文本没有包含Verilog,C++或者txt,clean无效')
                return msg
        def print_stream(stream):
            for s in stream:
                message = s["messages"][-1]
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print() 
        if not messages:
            if question:
                self.QUESTION=question
                self.MODULE=module
                
                if self.TESTBENCH:
                    inputs = {"messages": [("user", f"{self.Target}\n用户已存入testbench,无需调用工具生成")]}
                else: 
                    inputs = {"messages": [("user", f"{self.Target}")]}
                
                config = {"configurable": {"thread_id": thread_id},"recursion_limit": recursion_limit}
                        
                print_stream(agent.stream(inputs,config=config,stream_mode="values"))
        else:
            inputs = {"messages": [("user", f"{messages}")]}
            config = {"configurable": {"thread_id": thread_id},"recursion_limit": recursion_limit}
            self.QUESTION=messages
            for type,data in agent.stream(inputs,config=config,stream_mode=["messages",'updates']):
                if type=='messages':
                    if data[0].content and 'reactllm' in data[1].get("tags",[]):
                        print(data[0].content,end='',flush=True)
                    
                elif type=='updates':
                    for key,value in data.items():
                        if key=='agent':
                            for i in value['messages']:
                                if 'tool_calls' in i.additional_kwargs:
                                    for tool in i.additional_kwargs['tool_calls']:
                                        text=f"\n========== 工具调用 ==========\nindex:{tool['index']}\nid:{tool['id']}\n工具类型:{tool['type']}\n工具名称:{tool[tool['type']]['name']}\n工具参数:{tool[tool['type']]['arguments']}"
                                        print(text)
                        if key=='tools':
                            for i in value['messages']:
                                text=f"\n========== 工具执行回执 ==========\n工具名称:{i.name}\n工具ID:{i.id}\n工具调用ID:{i.tool_call_id}\n工具执行结果:{i.content}"
                                print(text)
            #print_stream(agent.stream(inputs,config=config,stream_mode="values"))

        if not self.result:
            self.one_shot=False
        return self.result
    
    def setquestion(self,question:str,module:str="",thread_id:str="1",newmemory:bool=False,TYPE:str="",maxitems:int=None,taskname:str=None,testbenchcode:str='',testbenchlc:str='',coverage_rigor:int=100,recursion_limit:int=100,reflc:str=''):
        self.QUESTION=question
        self.MODULE=module

    def modelinit(self,llmdict:dict=None):
        if not llmdict:
            llmdict={'generatellm':{'tags':["generatellm"]},
                     'evaluatellm':{'temperature':0.2,'tags':["evaluatellm"]},
                     'fixllm':{'temperature':0.7,'tags':["fixllm"]},
                     'verifyllm':{'tags':["verifyllm"]},
                     'testbenchllm':{'tags':["testbenchllm"]},
                     'reactllm':{'tags':["reactllm"]}}
        def initmodel(key_value):    
            key,value=key_value
            if  value:
                self.printc(key+':',end='')
                self.printc(value)
                setattr(self,key,self.llm.chat(model=self.modelname,**value))
            else:
                self.printc(key,end='')
                self.printc(':default')
                setattr(self,key,self.llm.chat(model=self.modelname))
        with ThreadPoolExecutor() as executor:
            executor.map(initmodel, llmdict.items())
    #工具定义
    def tools(self,coverage_rigor:int=100):
        #大模型代理可以调用的工具定义
        printc=print
        extract=self.extract
        savelog=self.savelog
        
        class SearchAgent(BaseModel):
            """在需要了解相关知识的情况下调用此tavily工具以实现搜索,根据输入的关键词获取相关知识,非必要不要调用此工具！"""
            keyword:str=Field(description="输入的以供搜索的关键词")
            model:str=Field(description="搜索的模式选项，选择'qna'以获得精准简洁的问题回答(推荐),选择'qa'以获得复杂详细的相关网页内容")
            include_domains:Sequence[str]=Field(description="搜索内容要包括的领域选项")
        @tool("searchagent",args_schema=SearchAgent)
        def searchagent(keyword:str,model:str='qna',include_domains:Sequence[str]=None):
            """在不了解相关知识的情况下调用此tavily工具以实现搜索,根据输入的关键词获取相关知识,,非必要不要调用此工具！"""
            savelog(f"\n## 搜索\n关键词为:{keyword}")
            if self.Tavilykey:
                tavily_client = TavilyClient(api_key=self.Tavilykey)
                if model=='qna':
                    response = tavily_client.qna_search(query=keyword,include_domains=include_domains,max_results=self.maxsearch)
                    savelog(f"\n搜索得到的结果:\n{response}")
                    return f"搜索得到的结果:\n{response}"
                elif model=='qa':
                    response = tavily_client.search(query=keyword,max_results=self.maxsearch,include_domains=include_domains)
                    savelog(f"\n搜索得到的结果:\n{response['results']}")
                    return f"搜索得到的结果:\n{response['results']}"
            else:
                return "未配置api,无法搜索"
        
        #代码生成工具
        class Generateagent(BaseModel):
            """调用此工具以实现代码的首次生成，根据用户输入的问题描述,参考提供的知识，生成初始代码并写入工作缓存,注意本工具只能使用一次,代码正常生成后通过fixagent修改代码"""
            knowledge:str=Field(description="调用搜索工具获得的相关知识信息，未调用搜索工具则填入0")
        @tool("generateagent",args_schema=Generateagent)
        def generateagent(knowledge:str='0'):
            """调用此工具以实现代码的首次生成，根据用户输入的问题描述,参考提供的知识，生成初始代码并写入工作缓存,注意本工具只能使用一次,代码正常生成后通过fixagent修改代码"""
            #运行时间获取
            now=datetime.now()
            generatetime = now.strftime("%Y-%m-%d_%H:%M:%S")
            savelog(f"\n# ----{generatetime}--------")
            if knowledge!="0":
                knowledge="\n相关知识解释:\n"+knowledge
                self.QUESTION+=knowledge
            printc(f"generateagent开始运行,llm输入为:\n{self.Problem}")
            #定义generateprompt
            if self.TYPE=="verilog":
                generateprompt=ChatPromptTemplate.from_messages(
                    [
                    ("system","你是一名专业的Verilog代码设计代理,处于代码自动设计流程的一环。你要充分理解用户提供的设计需求，并仔细推理如何一步一步解决问题。基于你的推理，输出满足要求的语法正确的verilog代码\n\n注意:\n1. 对于给定的问题，无论如何，你都需要自主设计出一个代码。\n2. 你所处的代码生成流程是自动化的，运行代码时无法从外部输入信息。设计代码时，你可以设计需要用户输入的功能，但为了能通过编译，你必须设置一个默认值\n3. 对于较复杂的问题，采用case语句而非逻辑表达式实现输出逻辑,对于dont'care的值没有明确说明时一律取x\n4. 不能在代码中添加任何注释以解释说明的内容\n5. 问题描述里给出的示例(如果有)非常重要,你必须确保你的推理和示例完全符合\n6. 你输出中的代码部分将被自动正则匹配提交给其他代理以进行后续的代码编译修正等,为了便于代码的自动化提取,确保输出最终代码时遵循以下格式：\n推理过程:\n填入你的推理过程\n完整代码实现:\n```verilog\n填入你所生成的完整代码\n```"),
                    ("human","{input}")
                    ]   
                )
            elif self.TYPE=="c++":
                generateprompt=ChatPromptTemplate.from_messages(
                    [
                    ("system","你是一名擅于设计C++代码进行物理计算分析的代理,处于代码自动设计流程的一环。你要充分理解用户提供的问题描述，并仔细推理如何一步一步解决问题。基于你的推理，输出满足要求的代码\n\n注意:\n1. 对于给定的问题，无论如何，你都需要自主设计出一个代码。\n2. 你所处的代码生成流程是自动化的，运行代码时无法从外部输入信息。设计代码时，你可以设计需要用户输入的功能，但为了能通过编译，你必须设置一个默认值\n3. 你输出中的代码部分将被自动正则匹配提交给其他代理以进行后续的代码编译修正等,为了便于代码的自动化提取,确保输出最终代码时遵循以下格式：\n推理过程:\n填入你的推理过程\n完整代码实现:\n```cpp\n填入你所生成的完整代码\n```"),
                    ("human","{input}")
                    ]   
                )

            generatechain=generateprompt|self.generatellm
            contents=generatechain.invoke({"input":f"{self.Problem}"}).content
            
            savelog(f'\n## 代码首次生成\n{self.Problem}\n\n{contents}')
            try:
                generatecode=extract(contents,f'{self.codetype}')
            except:
                printc(f"\nextract失败,generateagent的输出可能存在问题")
                savelog(f"\n## extract失败,generateagent的输出可能存在问题")
                return f"错误!!!工具输出未发现代码块,无法写入缓存！请检查:\n{contents}"
            #处理self.MODULE不符合预期的情况
            if self.TYPE=="verilog":
                if 'module' not in self.MODULE:
                    printc(f"模块声明定义为:{self.MODULE}\n其中没有发现'module'关键字,将使用代码生成的模块声明作为module声明")
                    modulematch= re.search(r'(module\s+\w+\s*\(.*?\))',self.QUESTION,flags=re.DOTALL)
                    if not modulematch:                    
                        printc(f"\n由于用户未提供模块声明,首次代码生成的模块声明语句将直接充当self.MODULE\n{self.MODULE}")
                        savelog(f"\n由于用户未提供模块声明,首次代码生成的模块声明语句将直接充当self.MODULE\n{self.MODULE}")
                        match= re.search(r'(module\s+.*?;)', generatecode,flags=re.DOTALL).group(1)
                        if match:
                            self.MODULE=match
                            printc(f"已将生成的模块声明语句作为self.MODULE\n{self.MODULE}")
                            savelog(f"self.MODULE已修改为:\n{self.MODULE}")
                        else:
                            printc(f"用户没有填入MODULE,生成的Verilog代码中尝试自动匹配模块声明失败")
            
            self.CODE=generatecode
            self.all+=1
            printc(f"已完成初次代码生成…………\n")
            return f"满足用户需求的代码已生成，可被其他工具读取"

        @tool("codecompile")
        def codecompile():
            """对生成的代码进行编译,返回输出和错误信息"""
            if not self.CODE:
                return "错误！没有在缓存中发现待编译代码"
            savelog(f"\n## 第{self.count+1}次编译")
            out,err=compile(code=self.CODE,type=self.TYPE,dir=os.path.join(self.dir,"runtemp"),taskname=self.taskname,extra_cmd="")
            self.count+=1
            printc(f"已完成第{self.count}次代码编译")
            if self.count==2:self.one_shot=False
            
            if err=="":#代码运行没有报错
                if out=="":    
                    return "通过编译,运行无输出"
                else:
                    if len(out)>900:
                        return f"{out[:900]}\n\n输出过长,已省略后续内容"
                    else:
                        return f"{out}"
            else:
                if '运行输出' in out:
                    savelog(f"编译正确,运行报错\n输出:{out}\n错误:\n{err}")
                    return f"编译正确,运行报错\n输出:{out}\n错误:\n{err}"
                else:
                    savelog(f"编译错误\n{out}\n{err}")
                    return f"编译错误\n{out}\n{err}"

        #评估代理，利用语言模型评估代码质量
        def evaluate(msg:str):
            evaluateprompt=ChatPromptTemplate.from_messages(
            [
                ("system", f"你是评估代码质量的专属代理,处于代码自动设计工作流程的一环。你将被提供一串代码,你需要从:可读性——代码的可理解清晰度。\n可维护性——代码更新或修改的便捷程度。\n鲁棒性——处理错误和异常的能力。\n标准合规性——代码与既定的{self.TYPE}编码标准的一致性\n等方面给代码打分,满分100分。为了便于正则匹配自动化提取,你需要将最终的打分输出为：\n```number\n你给定的分数\n```\n的格式"),
                ("human", "{input}"),
            ]
            )
            savelog('\n#### 代码评估\n')
            evaluatechain=evaluateprompt|self.evaluatellm
            evaluation=evaluatechain.invoke({"input":f"{msg}"}).content
            savelog(f"{evaluation}")
            number=extract(evaluation,'number')
            return number

        #代码比较回滚机制,code1为最初生成的代码,code2为修改后的代码,target为目标严格度，越小对代码修改要求越高
        def compare(code1:str,code2:str,target:int)->bool:
            if target==100:
                return True
            else:
                printc(f"正在调用compare对两个代码进行比较……\n")
                savelog(f"\n### 代码评分比较\n")
                evaluate1=int(evaluate(code1))
                savelog(f"#### 原代码评分：\n{evaluate1}")
                evaluate2=int(evaluate(code2))
                savelog(f"#### fixagent修改后代码评分:\n{evaluate2}")
                if evaluate1>evaluate2+target:
                    print(self.colored_text("\n代码修改失败,需要重新修改……\n",31))
                    return False   
                else:
                    print(self.colored_text("\n代码已修改成功,可覆盖原代码\n",32))
                    return True 

        #代码修正工具
        class Fixagent(BaseModel):
            """根据编译或验证后得到的错误信息,修改代码"""
            err: str = Field(description="对修正代码有帮助的全部输出和错误信息等")
            testbench:int=Field(description="对于Verilog,选择是否向工具提供testbench代码,1为提供,0为不提供(提供testbench将产生大量耗费,仅在极度需要时选择提供)")
        @tool("fixagent",args_schema=Fixagent)
        def fixagent(err:str,testbench:int=0):
            """根据编译或验证后得到的错误信息,修改代码.此工具并不读取用户提供的问题描述,调用时必要情况下需要额外提示"""
            if not self.CODE:
                return "没有在缓存中发现待修正代码，错误!"
            self.fixcount+=1
            
            if self.fixcount>=self.MAXITEMS:
                self.result=False
                self.lose+=1
                return "已达到工具调用阈值,请调用finaloutput提交最终代码"
            #testbench是否提供
            testbenchmsg=''
            if testbench==1 and self.fixcount>=4 and self.TYPE=="verilog":
                testbenchmsg=f'\n进行仿真测试的testbench为:\n```verilog\n{self.TESTBENCH}\n```'
            
            #RAG消息生成           
            rag=RAG(err,self.TYPE)
            if rag==[]:
                ragmsg=""
            else:
                ragmsg=f"\n{rag}"
            fixprompt=ChatPromptTemplate.from_messages(
                [
                    ("system",f"你被指定为修正{self.codetype}代码的专家。你的任务是接收一段需要修正的完整代码及其对应的编译或者检验仿真后得到的错误信息。基于提供的错误信息并结合历史修改方法，你需要逐步推理出错误信息出现的原因。并根据你的推理对代码进行修改以消除错误,最终给出无错满足要求的代码。\n注意:1. 只需要根据相关信息对提供的待修正代码完成修正，实现消除错误或者达成设定的代码目标。不要涉及目标代码外的任何代码\n2. 代码的修正是迭代式的，修正后的代码如再次报错会重新回到本环节，直至代码成功通过所有后续测试\n3. 提供的修正建议部分(若存在)是专家指出的可以消除错误的一般策略，需要重视并着重考虑\n4. 给出的修正代码不要包含任何进行解释标注的注释\n5. 对于已经尝试过的修正方式，保留错误更少的方式，若仍存在错误推理其他可能的原因，不要来回修改同一处\n6. 最终输出将用于后续的编译或进一步分析以进行迭代修正。为了便于自动化工具提取结果（正则表达式将匹配第一个代码块的内容作为修正后代码），请确保最终输出遵循以下格式：:\n推理过程:\n填入推理过程\n修正后的完整代码:\n```{self.codetype}\n填入修正后的完整代码\n```"),
                    MessagesPlaceholder(variable_name="history"),  # 记忆消息占位符
                    ("human","{input}")
                ]   
            )
            history_messages = self.fixmemory.messages
            fixchain=fixprompt|self.fixllm
            if self.fixcount<=2 :
                contents=fixchain.invoke({"input":f"错误信息与修改建议:\n{err}{ragmsg}{testbenchmsg}\n待修正代码:\n```\n{self.CODE}\n```\n代码目标:\n{self.Problem}","history": history_messages,}).content
                inputmsg=f"错误信息与修改建议:\n{err}{ragmsg}{testbenchmsg}\n待修正代码:\n```\n{self.CODE}\n```\n代码目标:\n{self.Problem}"
            elif ('Mismatches' in err) or ("不匹配" in err) or ("mismatches" in err) or ("mismatch" in err):
                contents=fixchain.invoke({"input":f"代码功能实现错误，着重考虑待修正代码功能实现(输出逻辑)与代码目标是否一致。\n错误信息与修改建议:\n仿真错误!\n{err}{ragmsg}{testbenchmsg}\n待修正代码:\n```\n{self.CODE}\n```\n代码目标:\n{self.Problem}","history": history_messages,}).content
                inputmsg=f"代码功能实现错误，着重考虑待修正代码功能实现与代码目标是否一致。\n错误信息与修改建议:\n仿真错误!\n{err}{ragmsg}{testbenchmsg}\n待修正代码:\n```\n{self.CODE}\n```\n代码目标:\n{self.Problem}"
            else:
                contents=fixchain.invoke({"input":f"错误信息与修改建议:\n{err}{ragmsg}{testbenchmsg}\n待修正代码:\n```\n{self.CODE}\n```","history": history_messages,}).content
                inputmsg=f"错误信息与修改建议:\n{err}{ragmsg}{testbenchmsg}\n待修正代码:\n```\n{self.CODE}\n```"
    
            savelog(f'\n## 第{self.fixcount}次代码修正\n{inputmsg}\n')  
            self.fixmemory.add_user_message(inputmsg)
            self.fixmemory.add_ai_message(contents)

            savelog(f"\n{contents}\n")
            try:
                fixcode=extract(contents,self.codetype)  
            except:
                return f"工具给出的结果没有识别到指定代码块,需要重新调用fixagent工具再次尝试修正"
            printc(f"已完成第{self.fixcount}次代码修正")
            printc(f"\n检查是否出现异常……\n")

            if compare(self.CODE,fixcode,coverage_rigor):
                self.CODE=fixcode
                
                printc(f"已完成代码修正")
                return f"代码已成功修正,使用codecompile进行编译验证"
            else:
                printc(f"代码修正未通过评估，未能修正代码")
                return f"代码修正出现错误,需要重新调用fixagent工具再次尝试修正"

        class Testbenchgeneration(BaseModel):
            """调用此工具以来为Verilog代码在验证仿真前生成testbench代码,便于后续仿真验证。此工具不可与verifyagent同时调用。对于同一问题描述,本工具只需要使用一次。当且仅当testbench存在问题时可调用此工具重新生成"""
            err: str = Field(description="上次提供的testbench代码仿真时出现的错误信息,没有错误则留空")
        @tool('testbenchgeneration',args_schema=Testbenchgeneration)
        def testbenchgeneration(err:str=""):
            """调用此工具以来为Verilog代码在验证仿真前生成testbench代码,便于后续仿真验证。此工具不可与verifyagent同时调用。对于同一问题描述,本工具只需要使用一次。当且仅当(本工具生成的)testbench存在问题时可调用此工具重新生成"""
            if self.testbench_generate_need:
                if err:
                    err='\n避免出现错误:'+err
                testprompt=ChatPromptTemplate.from_messages(
                    [
                    ("system", "你是专门为测试veriog代码生成testbench的专属代理,处于代码自动设计工作流程的一环。你需要根据给定信息生成带有test cases(覆盖全部情况)的testbench代码,以测试其他代理已经生成好的system verilog代码的功能正确性。  \n注意:  \n1. 除非特殊情况,均假定clock/clk正边沿触发。  \n2. 你生成的testbench代码应该能在iverilog,modelsim等软件下自动运行并且将仿真结果输出到控制台,输出的结果保证简洁直观。你必须让代码运行后输出Hint总结整体测试情况,提供精简但充分的错误信息以供修正，不要输出任何对改正代码没有帮助的信息,设计仿真运行输出时要模仿以下格式:   \nHint: Total mismatched samples is 1 out of 443 samples  \nSimulation finished at 50 ns\nMismatches: 0 in 443 samples \n3. 你输出的第一份代码块的内容将被自动正则匹配提交给其他代理以进行后续的代码仿真,为了便于代码的自动化提取,确保输出最终代码时遵循以下格式：\n你的分析等内容……  \n```verilog\n你所生成的testbench代码\n```"),
                    ("human", "{input}"),
                    ]
                )
                
                testbenchchain=testprompt|self.testbenchllm
                output=testbenchchain.invoke({"input":f"给定信息:\n{self.Problem}{err}"}).content
                printc(f"\n已完成testbench代码生成")
                savelog(f'\n## testbench代码生成\n给定信息:\n{self.Problem}{err}\n\n')
                savelog(output)
                try: self.TESTBENCH=extract(output,"verilog")
                except:
                    printc(f"testbenchgeneration出现错误,未提取到Verilog代码")
                    return f"出现错误!未成功生成testbench"

                return f"testbench代码已生成并保存"
            else:
                savelog('\n## testbench代码生成\n')
                savelog(f"testbench代码已存在,无需重复生成:\n+{self.TESTBENCH}")
                return f"testbench代码由用户提供,无需重复生成"

        #自我验证工具，验证代码功能实现
        class Verifyagent(BaseModel):
            """在代码已经没有语法错误之后,按照逻辑一步一步推断代码运行结果,判断代码实现功能是否与设计要求一致,返回验证结果"""
            message: str = Field(description="代码运行输出(如果非空)等有助于代码验证的相关信息,没有则填入0")
        @tool("verifyagent",args_schema=Verifyagent)
        def verifyagent(message:str="0"):
            """调用此工具以在代码没有语法错误后(Verilog代码需要确保已生成testbench代码),按照逻辑一步一步推断代码运行结果,判断功能实现是否与设计要求一致,返回验证结果"""
            savelog('\n## 代码自我验证\n')
            printc(f"\n正在调用verifyagent……\n")
            if message!="0":
                message="\n相关信息:"+message
            if self.TYPE=="verilog":
                if self.TESTBENCH=="":
                    return "未在缓存中发现testbench代码存在,请先调用testbenchgeneration工具生成testbench代码"
                else:
                    verifyprompt=ChatPromptTemplate.from_messages(
                            [
                            ("system", "作为验证Verilog代码功能正确性的专属代理，你需要根据提供的testbench代码，使用测试用例作为输入，逐时间步长逐步遍历代码以推断输出结果，从而测试Verilog代码是否满足设计要求。如果发现错误，需要返回失败的测试样例信息、错误原因和修改建议；这些信息将提交给专门负责修改代码的代理进行修正。如果testbench本身存在错误，也应在错误信息中明确指出。\n注意: \n1. 代码修改代理不了解testbench的具体内容，请确保提供的错误信息足够详细，以便他们能够准确理解问题所在。\n2. 无论正确错误,为了便于自动提取(text代码块中的内容将提交给修改代理作为指导),都需按此格式呈现结果：\n推理过程:\n填入你的推理过程\n```text\n通过功能测试\n``` \n\n或者\n\n推理过程:\n填入你的推理过程\n```text\n未通过功能测试\n错误信息:填入发现的错误\n有关信息:填入错误原因修改建议等\n```"),
                            ("human", "{input}"),
                            ]
                        )
                    verifychain=verifyprompt|self.verifyllm
                    verify=verifychain.invoke({"input":f"testbench:\n{self.TESTBENCH}\n问题描述：\n{self.Problem}\n完整的待验证代码:\n{self.CODE}{message}"}).content
                    savelog(verify)
                    cleanverify=extract(verify,'text')
            elif self.TYPE=="c++":
                verifyprompt=ChatPromptTemplate.from_messages(
                        [
                        ("system", "你是精通物理学知识以及善于利用cpp代码进行物理问题仿真与计算的专家代理。你需要按照逻辑一步一步的推理,遍历给定的代码，你可以假定输入来推断输出是否符合设计需求。如果发现错误,你需要返回详细的错误信息,你的输出信息将提交给其他专门的代码修改代理进行代码修正。\n注意:无论正确错误,为了便于自动提取(只有text代码块中的内容会提交给修改代理作为修改指导),你需要将结果输出为以下格式：\n推理过程:\n填入你的推理过程\n```text\n通过功能测试\n``` \n\n或者\n\n推理过程:\n填入你的推理过程\n```text\n未通过功能测试\n错误信息:填入发现的错误\n有关信息:填入错误原因修改建议等\n```"),
                        ("human", "{input}"),
                        ]
                    )
                verifychain=verifyprompt|self.verifyllm
                verify=verifychain.invoke({"input":f"问题描述：\n{self.Problem}\n完整的代码:\n{self.CODE}{message}"}).content
                savelog(verify)
                cleanverify=extract(verify,'text')
                if "未通过功能测试" not in cleanverify:
                    self.result=True

            return cleanverify

        @tool
        def simulator():
            """verilog代码通过自我验证后,调用此工具进行实际仿真,返回错误及输出等"""
            if self.taskname:
                self.savecode(self.CODE,f"{self.taskname}.sv")
            else:
                self.savecode(self.CODE,"temp.sv")    
            if not self.testbenchlc:
                if not self.TESTBENCH:
                    return "错误!未在缓存中发现testbench代码存在"
                else:
                    if self.taskname:
                        self.savecode(self.TESTBENCH,f"{self.taskname}_test.sv")
                        self.testbenchlc=os.path.join(self.dir,'runtemp','codetemp',f"{self.taskname}_test.sv")
                    else:
                        self.savecode(self.TESTBENCH,"testbenchtemp.sv")
                        self.testbenchlc=os.path.join(self.dir,'runtemp','codetemp',"testbenchtemp.sv")
            savelog('\n## verilog代码仿真\n')
            try:
                printc(f"正在调用iverilog进行仿真……\n")
                out,err=simulate(testbenchlc=self.testbenchlc,dir=os.path.join(self.dir,'runtemp'),reflc=self.reflc,taskname=self.taskname)
                printc(f"iverilog仿真完成")
            except:
                return "仿真运行失败,请检查代码"
            if err=="":#代码运行没有报错
                if out=="":
                    savelog("仿真无错,仿真无输出")    
                    return "通过仿真，无输出"
                else:
                    savelog(f"仿真输出:{out}")
                    match = re.search(r'Mismatches: (\d+) in \d+ samples', out)
                    if match:
                        mismatches = int(match.group(1))
                        if mismatches==0:
                            self.result=True
                    return f"仿真输出:{out}"
            else:
                savelog(f"仿真错误:{err}\n输出:{out}")
                return f"仿真错误:{err}\n输出:{out}"

        #最终输出工具，把代码保存到文件里
        class Finaloutput(BaseModel):
             """在代码已经通过编译与验证阶段后或者已经达到设定的工具调用阈值时，调用此工具可以把最终的代码提供给用户并清理运行缓存"""
             result: int = Field(description="代码是否通过全部工具测试,1为通过,0为未通过")
        @tool("finaloutput",args_schema=Finaloutput)
        def finaloutput(result:int):
            """在代码已经通过编译与验证阶段后或者已经达到设定的工具调用阈值时，调用此工具可以把最终的代码提供给用户并清理工作缓存"""
            #运行时间获取
            now=datetime.now()
            generatetime = now.strftime("%Y-%m-%d-%H_%M_%S")
            if self.CODE=="":
                return "在缓存中没有发现代码"
            else:
                if not self.taskname:
                    with open(os.path.join(self.dir,'runtemp','finalcode',f"finalcode_{generatetime}.txt"),"w+",encoding='utf-8') as f:
                        f.write(self.CODE)
                    printc(f"-------代码已经生成,生成时间为{generatetime},请查看本python代码同级runtemp/finalcode文件夹下的finalcode_{generatetime}.txt文件-------")
                else:
                    with open(os.path.join(self.dir,'runtemp','finalcode',f"{self.taskname}.txt"),"w+",encoding='utf-8') as f:
                        f.write(self.CODE)
                    printc(f"-------代码已经生成,生成时间为{generatetime},请查看本python代码同级runtemp/finalcode文件夹下的{self.taskname}.txt文件-------")
                if result==0:
                    self.result=False
                savelog('\n## 最终代码\n')
                savelog('```\n'+self.CODE+'\n```')
                return f"完成"

        @tool
        def cleanmemory():
            """没有要使用finaloutput工具保存最终代码时，调用此工具清理缓存来结束任务"""
            self.QUESTION=""
            self.MODULE=""
            self.TESTBENCH=""
            self.CODE=""
            self.count=0
            return "已结束"
        
        class Savetotemp(BaseModel):
            """多次(两次以上)调用generateagent生成代码始终出错时，调用此工具暂时代替完成`generateagent`的工作,以使流程正常完成。正常情况下不得调用此工具"""
            code:str=Field(description="异常情况下，你自己写的满足用户需求的代码(完整且可直接运行)")
        @tool("savetotemp",args_schema=Savetotemp)
        def savetotemp(code:str):
            """多次(两次以上)调用generateagent生成代码始终出错时，调用此工具暂时代替完成`generateagent`的工作,以使流程正常完成。正常情况下不得调用此工具"""
            #运行时间获取
            now=datetime.now()
            generatetime = now.strftime("%Y-%m-%d_%H:%M:%S")
            savelog(f"\n# ----{generatetime}--------")
            self.CODE=code
            savelog(f"\n## 手动保存代码\n```code\n{code}\n```")
            printc(f"已手动保存代码")
            return f"已将代码写入缓存,可被其他工具应用"
        
        #运行单个工具
        def runtool(name:str,*args,**kwargs):
            toolmap={'generateagent':generateagent,'codecompile':codecompile,'fixagent':fixagent,'testbenchgeneration':testbenchgeneration,'verifyagent':verifyagent,'simulator':simulator,'finaloutput':finaloutput,'cleanmemory':cleanmemory,'savetotemp':savetotemp}
            if name in toolmap:
                toolmap[name].func(*args,**kwargs)
            else:
                return f"未找到名为{name}的工具"
            
        #工具全定义完成，集合到列表里
        if self.TYPE=="verilog": 
            if self.testbench_generate_need:
                tools=[generateagent,codecompile,fixagent,testbenchgeneration,verifyagent,simulator,finaloutput,savetotemp]
            else:                
                tools=[generateagent,codecompile,fixagent,verifyagent,simulator,finaloutput,savetotemp]
            
        elif self.TYPE=='c++':
            tools=[generateagent,codecompile,fixagent,verifyagent,finaloutput,savetotemp]
        if self.Tavilykey:
            tools.append(searchagent)
        self.runtool=runtool
        return tools
    
    def newvcagent(self,newmemory:bool=False,coverage_rigor:int=100,TYPE:str="",maxitems:int=None):
        if newmemory:
              self.cleantemp()
        if TYPE:
            self.TYPE=TYPE
        if maxitems:
            self.MAXITEMS=maxitems

        agent=create_react_agent(self.reactllm,tools=self.tools(coverage_rigor),checkpointer=self.memory, prompt=self.identity)
        return agent
    
    def cleantemp(self):
        self.QUESTION=""
        self.MODULE=""
        self.TESTBENCH=""
        self.CODE=""
        self.fixcount=0
        self.fixmemory=InMemoryChatMessageHistory(session_id="fix-session")
        self.count=0
        self.taskname=''
        self.testbenchlc=''
        self.reflc=''
        self.result=False
        self.testbench_generate_need=True
        self.memory=MemorySaver()
        self.one_shot=True
    
    def problemreset(self):
        self.QUESTION=""
        self.MODULE=""
        self.TESTBENCH=""
        self.count=0
        self.testbenchcode=''
    @property
    def Problem(self):
        if self.TYPE=="verilog":
            if self.MODULE=="":
                problem="根据以下描述完成verilog模块设计。除非特殊情况,均假定clock/clk正边沿触发\n问题描述:\n"+self.QUESTION
            else:
                problem="根据以下描述完成verilog模块设计。除非特殊情况,均假定clock/clk正边沿触发\n问题描述:\n"+self.QUESTION+"\n\n模块头:\n"+self.MODULE
        elif self.TYPE=="c++":
            problem="根据以下描述生成C++代码以解决物理问题.\n问题描述:\n"+self.QUESTION+'\n'
        return problem

    @property
    def Target(self):
        if self.TYPE=="verilog":
            if self.MODULE=="":
                target="根据以下描述完成verilog模块设计,确保最后用finalout工具给出没有任何error甚至warning的代码。除非特殊情况,均假定clock/clk正边沿触发\n问题描述:\n"+self.QUESTION
            else:
                target="根据以下描述完成verilog模块设计,确保最后用finalout工具给出没有任何error甚至warning的代码。除非特殊情况,均假定clock/clk正边沿触发\n问题描述:\n"+self.QUESTION+"\n\n模块头:\n"+self.MODULE
        elif self.TYPE=="c++":
            target="根据以下描述生成C++代码以解决物理问题,确保最后用finalout工具给出没有任何error甚至warning的代码。\n问题描述:\n"+self.QUESTION+'\n'
        return target
    @property
    def identity(self):
        if self.TYPE=="verilog":
            #return"你是中国东南大学的专属ReAct代理,精通使用Verilog进行电路设计的各种相关知识。你要通过以下步骤,自主利用提供的工具帮助用户生成没有任何错误的verilog代码\n任务流程:\n使用generateagent工具首次生成满足用户需求的代码,使用codecompile工具编译生成的代码以测试是否存在语法错误,使用fixagent工具根据反馈的输出错误信息对代码进行修改。确认没有语法错误之后,若用户没有存入testbench代码,则用testbenchgeneration工具生成,再使用verifyagent工具验证代码功能是否正确,通过功能验证后使用simulator进行实践仿真。注意一旦对代码有任何修改,都必须重新进行codecompile测试。当代码成功通过全部编译-验证-仿真后,必须在最后调用finaloutput工具将代码提交给用户才能结束任务。\n注意:\n1. 一次只调用一个工具\n2. 用户输入的问题描述模块头以及最终输出的代码等都将直接写入缓存，不需重复输入\n3. 你所处的代码生成流程是自动化的，因此编译之类的环节中无法从外部输入信息,这是可能的编译超时的原因\n4. 调用完finaloutput工具后,你只需以'所需代码已保存'结束对话\n5. 除非指定或已达到限制,你必须在代码已经全部成功通过编译、验证、仿真等一系列测试后才能结束任务\n6. 整个流程你要尽量减少输出量,降低花费"

            return """你作为中国东南大学的专属ReAct代理，精通使用Verilog进行电路设计的相关知识。你的任务是通过一系列自动化步骤帮助用户生成语法正确(能通过编译,无错误乃至警告)、功能正确(仿真无错或者没有不匹配的出现)的无误的Verilog代码。你要严格遵照以下具体流程直至完成轮次任务：
- **一**：利用`generateagent`工具根据用户需求首次给出代码。当且仅当两次以上调用generateagent工具都出错后，使用`savetotemp`工具代替完成代码生成的任务。其余情况不得调用'savetotemp'工具。
- **二**：使用`codecompile`工具编译生成的代码以检测是否存在语法错误。
- **三**：若编译（以及任何其他过程中）发现代码存在错误，则调用`fixagent`工具基于反馈信息修正代码，并回到第二步重新开始执行流程。
- **四**：判断是否存在testbench代码,判断用户是否提供testbench代码。若用户提供testbench代码，则testbench绝对正确无误,不可更改,且不可使用testbenchgeneration工具。仅在用户未提供测试平台（testbench）代码的情况下，在没有testbench代码或者需要修改已有testbench代码时,使用`testbenchgeneration`工具生成testbench(一般只需调用工具生成一次)。
- **五**：运用`verifyagent`工具验证代码的功能正确性。若未通过功能验证，则返回到第三步使用`fixagent`工具进行修正。通过则继续下一步。
- **六**：功能验证通过后，使用`simulator`工具进行实际仿真测试。若通过仿真，则使用`finaloutput`工具将代码提交给用户。；若未通过，则返回到第三步。
- **七**：对代码进行了任何修改后，必须重新回到第二步执行所有后续步骤。
### 注意事项：
1. 每次仅能调用一个工具。且在完成任务前你必须自主推理或者调用工具，不得询问用户或者与用户对话。
2. 用户提供的问题描述、模块头文件以及最终输出的代码等信息会直接保存在缓存中，无需再次输入。
3. 由于整个过程为自动化操作，在如编译这样的环节中无法接收外部输入，这可能是导致编译超时的原因之一。
4. 你必须以调用`finaloutput`工具来结束本轮次的任务。且调用了`finaloutput`工具后，你只需以'所需代码已保存'结束对话。
5. 你必须在代码已经全部成功通过编译、验证、仿真等一系列测试后才能结束任务。
6. 由'testbenchgeneration'工具产生的testbench代码可能存在问题,若testbench代码出现问题,不调用fixagent工具，而是调用`testbenchgeneration`工具重新生成testbench代码。但当testbench代码是由用户给定时,认为其绝对正确,不能也不需作任何修改。
7. 必须在多次尝试仍没有使代码仿真不匹配数减少后，你才能向'fixagent'工具提供testbench代码以降低花费
8. 整个工作流中应尽量减少不必要的输出，以降低花费。
请严格按照上述指导原则操作，确保为用户提供高质量的服务体验。"""
            
        elif self.TYPE=="c++": 
            #return"你是中国东南大学物理学院的专属代理,精通各种物理学知识,熟练利用C++代码进行各种仿真和计算研究,你要通过以下步骤,自主利用提供的工具帮助用户生成没有任何错误的cpp代码\n任务流程:\n使用generateagent工具首次生成满足用户需求的代码,使用codecompile工具编译生成的代码以测试是否存在语法错误,使用fixagent工具根据反馈的输出错误信息对代码进行修改。没有语法错误之后,使用verifyagent工具验证代码功能是否正确。注意一旦对代码有任何修改,都必须重新进行codecompile测试。当代码成功通过全部编译-验证后,必须在最后调用finaloutput工具将代码提交给用户才能结束任务。\n注意:\n1. 一次只调用一个工具\n2. 用户输入的问题描述模块头以及最终输出的代码等都将直接写入缓存，不需重复输入\n3. 你所处的代码生成流程是自动化的，因此编译之类的环节中无法从外部输入信息,这是可能的编译超时的原因\n4. 调用完finaloutput工具后,你只需要告诉用户'所需代码已保存'即可，不要说任何其他信息\n5. 除非指定或已经达到限制,你必须在代码已经成功通过编译验证等一系列测试后才能提交给用户\n6. 整个流程你要尽量减少输出量,降低花费"
            return """你将作为中国东南大学物理学院的专属ReAct代理,负责帮助用户生成语法正确(能通过编译,无错误乃至警告)、功能正确(通过功能验证)的无误的C++代码。你的任务包括但不限于利用物理学知识进行物理仿真和计算研究。你要严格遵照以下具体流程直至完成轮次任务：
1. 使用`generateagent`工具根据用户需求首次生成代码。当且仅当多次(两次以上)调用generateagent工具始终出错后，使用`savetotemp`工具代替完成代码生成的任务。其余情况不得调用'savetotemp'工具。
2. 通过`codecompile`工具对生成的代码进行编译，以检测是否存在语法错误。
3. 若编译（以及任何其他过程中）发现代码存在错误，则调用`fixagent`工具基于反馈信息修正代码，并回到第二步重新开始执行流程。
4. 代码不存在语法问题后，使用`verifyagent`工具验证代码功能是否正确。若未通过功能验证，则返回到第三步使用`fixagent`工具进行修正。通过则继续下一步。
5. 通过功能验证后，调用`finaloutput`工具将最终版本的代码提交给用户。
6. 对代码进行了任何修改后，必须重新回到第二步执行所有后续步骤。

### 注意事项：
- 每次仅能调用一个工具。且在完成任务前你必须自主推理或者调用工具，不得询问用户或者与用户对话。
- 用户提供的问题描述及最终输出的代码等信息会直接存储于缓存中，无需重复输入。
- 由于整个流程是自动化的，在编译等环节无法接收外部输入，这可能是导致编译超时的原因之一。
- 你必须以调用`finaloutput`工具来结束本轮次的任务。且调用`finaloutput`工具后，你只需以'所需代码已保存'结束对话。
- 你必须在代码已经全部成功通过编译、验证等一系列测试后才能结束任务。
- 尽量减少不必要的输出，保持简洁高效以降低资源消耗。

请严格按照上述指导原则操作，确保为用户提供高质量的服务体验。"""

    @property
    def codetype(self):
        if self.TYPE=="verilog":
            return "verilog"
        elif self.TYPE=="c++":
            return "cpp"
        
#response = print_stream(agent_runnable.stream(inputs,config=config,stream_mode="values"))
if __name__=="__main__":
    if apikey and Tavilykey:
        test=Newvc(apikey=apikey,Tavilykey=Tavilykey,TYPE='verilog')
    a=True
    b=False
    while a:
        humanmessage=input("\n请输入内容(exit以退出):").strip()
        sys.stdout.write("\033[F\033[K")  # 光标上移一行并清除
        sys.stdout.flush()
        if humanmessage=="exit":
            break
        elif humanmessage=="new":
            test.cleantemp()
        else:
            test.run(messages=humanmessage)

    question="""The game Lemmings involves critters with fairly simple brains. So simple
that we are going to model it using a finite state machine. In the
Lemmings' 2D world, Lemmings can be in one of two states: walking left
(walk_left is 1) or walking right (walk_right is 1). It will switch
directions if it hits an obstacle. In particular, if a Lemming is bumped
on the left (by receiving a 1 on bump_left), it will walk right. If it's
bumped on the right (by receiving a 1 on bump_right), it will walk left.
If it's bumped on both sides at the same time, it will still switch
directions.

In addition to walking left and right and changing direction when bumped,
when ground=0, the Lemming will fall and say ""aaah!"". When the ground
reappears (ground=1), the Lemming will resume walking in the same
direction as before the fall. Being bumped while falling does not affect
the walking direction, and being bumped in the same cycle as ground
disappears (but not yet falling), or when the ground reappears while
still falling, also does not affect the walking direction.

In addition to walking and falling, Lemmings can sometimes be told to do
useful things, like dig (it starts digging when dig=1). A Lemming can dig
if it is currently walking on ground (ground=1 and not falling), and will
continue digging until it reaches the other side (ground=0). At that
point, since there is no ground, it will fall (aaah!), then continue
walking in its original direction once it hits ground again. As with
falling, being bumped while digging has no effect, and being told to dig
when falling or when there is no ground is ignored. (In other words, a
walking Lemming can fall, dig, or switch directions. If more than one of
these conditions are satisfied, fall has higher precedence than dig,
which has higher precedence than switching directions.)

Although Lemmings can walk, fall, and dig, Lemmings aren't invulnerable.
If a Lemming falls for too long then hits the ground, it can splatter. In
particular, if a Lemming falls for more than 20 clock cycles then hits
the ground, it will splatter and cease walking, falling, or digging (all
4 outputs become 0), forever (Or until the FSM gets reset). There is no
upper limit on how far a Lemming can fall before hitting the ground.
Lemmings only splatter when hitting the ground; they do not splatter in
mid-air.

Implement a Moore state machine that models this behaviour. areset is
positive edge triggered asynchronous reseting the Lemming machine to walk
left."""
    module="""module TopModule (
  input clk,
  input areset,
  input bump_left,
  input bump_right,
  input ground,
  input dig,
  output walk_left,
  output walk_right,
  output aaah,
  output digging
);"""
    #test.run(question="写一个自由落体仿真运动的仿真代码")
    #test.run(question=question,module=module)
    #print(type(test.generatellm))