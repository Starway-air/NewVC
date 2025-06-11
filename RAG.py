
def RAG_iverilog(error_message:str):
    extra_msg = []
    if 'Timeout' in error_message:
        extra_msg.append("* 自动化运行无法进行外部输入操作，若代码存在外界输入的内容，可以预设默认值")
    if 'Unable to bind wire/reg/memory' in error_message:
        extra_msg.append("* replace 'posedge clk' with '*'")
    if 'dangling input port' in error_message and '(clk) floating' in error_message:
        if 'posedge clk' in error_message:
            extra_msg.append("* replace 'posedge clk' with '*'")
        else:
            extra_msg.append("* remove clk from input")
    if 'not a valid l-value' in error_message:
        extra_msg.append('* next_state is defined as a wire not reg, it is not a valid l-value. Use assign statements instead of always block if possible.')
    if error_message == 'syntax error' or 'I give up' in error_message:
        extra_msg.append('* 检查待修正verilog代码是否完整可运行,是否包含模块声明语句，确保已包含模块声明语句等必要内容。另外若提供的待修正代码并非代码格式，可能说明此前你的输出格式不规范导致提取错误，需要改变输出格式保证正确提取到修正后代码')
#         if not selff._verify_module_header(code_completion, self.test_suite['prompt']):
#             extra_msg.append(f"* The implementation must be based on the following module header: {self.test_suite['prompt']}")
    if "invalid module instantiation" in error_message.lower():
        extra_msg.append("* Implement all logic inside top_module. Do not instantiation module inside top_module. Please correct the code and run compile again.")
#         if 'give up' in error_message:
#             extra_msg.append("* Ignore the previous implementation and create a new implementation from scratch.")
    if "Extra digits given for sized binary constant." in error_message:
        extra_msg.append("* Please make sure that your binary numbers have exactly digits, consisting of 0s and 1s, as specified in the declaration (e.g., 9'b0000000001). Extra digits are not allowed.")
    if "Unknown module type:" in error_message:
        extra_msg.append("* 目标代码的模块名可能与testbench设定的模块名称不一致，建议修改目标代码模块名使得与testbench模块名保持一致")
    if "Static variable initialization requires explicit lifetime in this context" in error_message:
        extra_msg.append("""* 不要在声明变量时初始化它们。请在always块中使用非阻塞赋值语句（<=）来初始化变量。""")
    if "constant selects in always_* processes are not currently supported (all bits will be included)" in error_message:
        extra_msg.append("""* case语句块内不支持拼接操作,考虑是否需拼接操作，无法避免可选择在case语句外进行拼接""")
    if "mismatch" in error_message or 'Mismatch' in error_message or "不匹配" in error_message:
        extra_msg.append("""* 如果是状态机实现，注意状态转换的延时问题，检查时序是否正确,特定状态内的计数会延迟一个周期开始，尝试对设定的计数次数减一""")
    if extra_msg:
        extra_msg = ['修正建议:'] + extra_msg
    else:
        extra_msg = ""

    return extra_msg

def RAG_cpp(error_message:str):
    extra_msg = []
    if 'Timeout' in error_message:
        extra_msg.append("* 自动化运行无法进行外部输入操作，若代码存在外界输入的内容，可以预设默认值")
    if 'No such file or directory' in error_message :
        extra_msg.append("* 如果调用库报错，原因为当前运行环境未配置当前调用的库，可尝试其他库或使用其他方法实现相同功能")
    if extra_msg:
        extra_msg = ['修正建议:'] + extra_msg
    else:
        extra_msg = ""

    return extra_msg
    
def RAG(error_message:str,TYPE:str):
    if TYPE=='verilog':
        return RAG_iverilog(error_message)
    elif TYPE=='c++':
        return RAG_cpp(error_message)
    
print(RAG('error','c++'))