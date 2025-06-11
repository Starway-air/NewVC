from langchain_deepseek import ChatDeepSeek

modeldict={'deepseek':{'model':'deepseek-chat','api_key':None,'api_base':'https://api.deepseek.com'},
           'siliconflow':{'model':'deepseek-ai/DeepSeek-V3','api_key':None,'api_base':'https://api.siliconflow.cn/v1'},
           'qwen':{'model':'qwen-turbo','api_key':None,'api_base':'https://dashscope.aliyuncs.com/compatible-mode/v1'},
           }

class Models():
    def __init__(self,allmodel:dict=modeldict,modeltype:str=None,model:str=None,api_key:str=None,api_base:str=None):
        self.modeldict=allmodel
        self.default='deepseek'
        if modeltype:
            self.add(modeltype,model,api_key,api_base)
            self.default=modeltype

    def judgein(self,modeltype:str):
        if modeltype not in self.modeldict:
            raise ValueError(f"在支持的全部模型列表中未发现modeltype:{modeltype}")
        else:
            self.default=modeltype

    #将模型加入支持列表
    def add(self,modeltype:str,model:str,api_key:str=None,api_base:str=None):
        self.default=modeltype
        if api_base:
            self.modeldict[modeltype]={'model':model,'api_key':api_key,'api_base':api_base}
        else:
            self.modeldict[modeltype]={'model':model,'api_key':api_key}

    #获取模型参数
    def get(self,modeltype:str=None,model:str=None,api_key:str=None):
        if modeltype:
            self.judgein(modeltype)        
        if api_key:
            self.modeldict[self.default]['api_key']=api_key
        else:
            if not self.modeldict[self.default]['api_key']:
                raise ValueError(f"当前{self.default}模型未设置api_key,请先设置api_key")
            
        modelreturn=self.modeldict[self.default]
        if model:#如果用户特别设置了model，则使用用户设置的model
            modelreturn['model']=model
        return modelreturn
    #对支持列表中的某个模型设置api_key
    def set(self,api_key,modeltype:str=None):
        if modeltype:
            self.judgein(modeltype)
        self.modeldict[self.default]['api_key']=api_key

    def chat(self,modeltype:str=None,max_retries:int=2,model:str=None,api_key:str=None,api_base:str=None,**kwargs):
        if modeltype:
            self.default=modeltype
            if modeltype not in self.modeldict.keys():
                self.add(modeltype,model,api_key,api_base)
                return ChatDeepSeek(**self.modeldict[self.default],max_retries=max_retries,**kwargs)
        for key,value in {'model':model,'api_key':api_key,'api_base':api_base}.items():
            if value:
                self.modeldict[self.default][key]=value

        return ChatDeepSeek(**self.modeldict[self.default],max_retries=max_retries,**kwargs)
                
        
if __name__=='__main__':
    a=Models()
    a.set('sk-xxxx','deepseek')
    print(a.get('deepseek'))
    a.add('siliconflow','siliconflow-ai/DeepSeek-V3','sk-xxxx','https://api.siliconflow.cn/v1')
    print(a.get('siliconflow'))
    a.set('sk-xxx')
    print(a.get())
