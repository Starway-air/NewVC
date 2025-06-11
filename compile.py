import subprocess
import os
import sys

patha = os.path.dirname(os.path.realpath(sys.argv[0]))  # 获取当前脚本所在目录

def compilestart(code:str,type:str,dir:str,taskname:str='',extra_cmd:str=""):
    if type=="verilog":
       if taskname:
           file_path = os.path.join(dir,"codetemp",f"{taskname}.sv")
       else:file_path = os.path.join(dir,"codetemp","temp.sv")  # 创建文件路径
       with open(file_path, "w",encoding='utf-8') as f:
           f.write(code)
           f.close()
           text=f"iverilog -Wall -Winfloop -Wno-timescale -g2012 {extra_cmd} -o {dir}/compiletemp/test.vvp  {file_path}"
           text1=f"vvp {dir}/compiletemp/test.vvp"
           return text,text1
    elif type=="c++":
        if taskname:
           file_path = os.path.join(dir,"codetemp",f"{taskname}.cpp")
        else:file_path = os.path.join(dir,"codetemp","temp.cpp")  # 创建文件路径
        with open(file_path, "w",encoding='utf-8') as f:
            f.write(code)
            f.close()
            text=f"g++ -std=c++11 -Wall -Wextra  {extra_cmd} -o {dir}/compiletemp/test  {file_path}"
            text1=os.path.join(dir,"compiletemp","test")
            return text,text1
    else:
        print("compile,类型输入错误")
        raise ValueError("compile,类型输入错误")        

def run(text:str,time=20):
    x=subprocess.run(text,shell=True,timeout=time,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    out,err=x.stdout,x.stderr
    return out,err

    
def compile(code:str,type:str,dir:str,taskname:str='',extra_cmd:str="",time:int=20):
    text,text1=compilestart(code,type,dir,taskname,extra_cmd)
    out,err=run(text,time)
    if err=="":
        out1,err1=run(text1,time)
        if out1!="":
            out = '没有错误\n编译输出:'+out + '\n运行输出:\n' + out1
        err = err1
        return out,err
    else:
        return out,err
    
def simulatestart(dir:str,testbenchlc:str,veriloglc='',taskname:str='',reflc:str='',extra_cmd:str="",):
    if taskname:
           file_path = os.path.join(dir,'codetemp',f"{taskname}.sv")
    else:file_path = os.path.join(dir,'codetemp',"temp.sv")
    if veriloglc:
        file_path = veriloglc
    text=f"iverilog -Wall -Winfloop -Wno-timescale -g2012 {extra_cmd} -o {dir}/compiletemp/test.out  {file_path} {testbenchlc} {reflc}"
    text1=f"vvp {dir}/compiletemp/test.out"
    return text,text1

def simulate(dir:str,testbenchlc:str,veriloglc:str='',reflc:str='',taskname:str='',extra_cmd:str="",time:int=20):
    text,text1=simulatestart(dir=dir,taskname=taskname,testbenchlc=testbenchlc,reflc=reflc,veriloglc=veriloglc,extra_cmd=extra_cmd)
    out,err=run(text,time)
    if err=="":
        out1,err1=run(text1,time)
        if out1!="":
            out = out1
        err = err1
        return out,err
    else:
        return out,err

if __name__=="__main__":
    test=f'iverilog -Wall -Winfloop -Wno-timescale -g2012  -o {patha}/runtemp/compiletemp/test.vvp  {patha}/verilog-eval-main/dataset_code-complete-iccad2023/Prob001_zero_ref.sv'
    test1=f'vvp {patha}/runtemp/compiletemp/test.vvp'
    test2=f'iverilog -Wall -Winfloop -Wno-timescale -g2012  -o {patha}/runtemp/compiletemp/test1.out {patha}/verilog-eval-main/dataset_code-complete-iccad2023/Prob001_zero_test.sv  {patha}/verilog-eval-main/dataset_code-complete-iccad2023/Prob001_zero_ref.sv {patha}/runtemp/compiletemp/temp.sv'
    test3=f'vvp {patha}/runtemp/compiletemp/test1.out'
    
    #a=simulate(f'{patha}/runtemp/compiletemp',f'{patha}/verilog-eval-main/dataset_code-complete-iccad2023/Prob001_zero_test.sv',f'{patha}/verilog-eval-main/dataset_code-complete-iccad2023/Prob001_zero_ref.sv')
    #b=simulate(f'{patha}/runtemp/compiletemp','/mnt/d/Downloads/newvc/verilog-eval-main/dataset_code-complete-iccad2023/Prob152_lemmings3_test.sv','/mnt/d/Downloads/newvc/runtemp/compiletemp/Prob152_lemmings3.sv','/mnt/d/Downloads/newvc/verilog-eval-main/dataset_code-complete-iccad2023/Prob152_lemmings3_ref.sv')
    #print(b)
    cpp='#include<iostream>\nusing namespace std;\nint main(){\ncout<<"hello world"<<endl;\nreturn 0;\n}'
    print(compile(cpp,'c++',f'{patha}/runtemp/compiletemp'))
