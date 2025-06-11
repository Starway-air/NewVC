D:/Anaconda3/envs/dl/python.exe -m nuitka --standalone --onefile \
               --enable-plugin=pyside6 \
               --include-module=newvcforapp \
               --include-module=storage2 \
               --include-data-files=resources.py=resources.py \
               --windows-icon-from-ico=myapp.ico \
               --windows-console-mode=disable \
               myapp.py