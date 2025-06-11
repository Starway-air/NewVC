# NewVC
一款基于AI的对话式代码自动生成与纠正软件
主要是对于物理计算C++和电路设计Verilog代码的自动修正
底层使用Langchain框架，ui使用pyside6
需要的python包为：
 - langchain
 - langchain_deepseek
 - langgraph
 - openai
 - pydantic
 - tavily_python
 - pyside6
   
需要预先设置好的代码编译器为：
 - C++：[MingW](https://github.com/niXman/mingw-builds-binaries)
 - Verilog：[iverilog](https://github.com/steveicarus/iverilog)

系统工作流程如图所示：
[resources/anounce/intro.svg](https://raw.github.com/Starway-air/NewVC/blob/main/resources/anounce/intro.svg)
