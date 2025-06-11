import sys
import asyncio
from os import path
from contextlib import contextmanager
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout,QStackedWidget, QLabel,QPushButton,QMainWindow,QSizePolicy,QScrollArea,QTextEdit,QFormLayout,QTextBrowser,QFrame,QComboBox,QLineEdit,QMenu,QToolButton,QGridLayout,QFileDialog,QDialog,QCheckBox,QMessageBox,QApplication,QStyleFactory
from PySide6.QtCore import Qt, QSize, QEvent,QPropertyAnimation,Property, QEasingCurve,QTimer,Slot,QMetaObject,Q_ARG,QThread,QObject,Signal,QSettings,QCoreApplication,QFile
from PySide6.QtGui import QIcon, QPixmap, QPainter,QColor,QPainterPath,QTextOption,QAction,QActionGroup,QMovie
from openai import base_url
from newvcforapp import Newvc
from storage2 import AccountManager
import resources

class OutputCapture:
    def __init__(self, signal):
        self.signal = signal
        self.buffer = []
    
    def write(self, text):
        self.buffer.append(text)
        if text.endswith('\n'):
            self.signal.emit(''.join(self.buffer).strip())
            self.buffer = []
    
    def flush(self):
        pass

@contextmanager
def capture_outputs(signal):
    import sys
    old_stdout = sys.stdout
    capturer = OutputCapture(signal)
    sys.stdout = capturer
    try:
        yield
    finally:
        sys.stdout = old_stdout

class AIWorker(QObject):
    finished = Signal()
    err_occured = Signal(str)
    chunk_received = Signal(str)
    update_finished=Signal()
    other_received=Signal(str)
    log_received=Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True

    def stop(self):
        self._is_running = False
    def process_request(self, text,agent):
        try:
            with capture_outputs(self.log_received):
                inputs = {"messages": [("user", f"{text}")]}
                config = {"configurable": {"thread_id": 1},"recursion_limit": 50}
                for type, data in agent.stream(inputs, config=config,stream_mode=["messages", "updates"],):
                    if not self._is_running:
                        print("\n中止……")
                        # agent.interrupt(config)
                        break
                    if type=='messages':
                        if data[0].content and 'reactllm' in data[1].get("tags",[]):
                            chunk = data[0].content
                            self.chunk_received.emit(chunk)
                            QThread.msleep(10)
                    elif type=='updates':
                        for key,value in data.items():
                            if key=='agent':
                                for i in value['messages']:
                                    if 'tool_calls' in i.additional_kwargs:
                                        for tool in i.additional_kwargs['tool_calls']:
                                            text=f"=======工具调用=======  \nindex:{tool['index']}  \nid:{tool['id']}  \n工具类型:{tool['type']}  \n工具名称:{tool[tool['type']]['name']}  \n工具参数:{tool[tool['type']]['arguments']}"
                                            self.other_received.emit(text)
                            if key=='tools':
                                for i in value['messages']:
                                    text=f"=======工具执行结果=======  \n工具名称:{i.name}  \n工具ID:{i.id}  \n工具调用ID:{i.tool_call_id}  \n工具执行结果:  \n{i.content}"
                                    self.other_received.emit(text)
                self._is_running = True
                self.finished.emit()
                #     if msg_type == "messages":
                #         if data[0].content and 'reactllm' in data[1].get("tags",[]):
                #             buffer+=data[0].content
                #             #print(f'{data[0].content}',end='')
                #             if len(buffer) > 50:
                #                 self.chunk_received.emit(buffer)
                #                 buffer = ""
                #                 QThread.msleep(10)  # 稍微释放控制权
                # if buffer:
                #     self.chunk_received.emit(buffer)
                # self.finished.emit()
                

        except Exception as e:
            self.err_occured.emit(f"[ERROR] {str(e)}")
            self.finished.emit()

    async def async_process_request(self, text, agent):
        try:  
            inputs = {"messages": [("user", f"{text}")]}
            config = {"configurable": {"thread_id": 1},"recursion_limit": 50}
            with capture_outputs(self.log_received):
                inputs = {"messages": [("user", f"{text}")]}
                config = {"configurable": {"thread_id": 1},"recursion_limit": 50}
                for type, data in agent.astream(inputs, config=config,stream_mode=["messages", "updates"]):
                    if type=='messages':
                            if data[0].content and 'reactllm' in data[1].get("tags",[]):
                                chunk = data[0].content
                                self.chunk_received.emit(chunk)
                                QThread.msleep(10)
                    elif type=='updates':
                        for key,value in data.items():
                            if key=='agent':
                                for i in value['messages']:
                                    if 'tool_calls' in i.additional_kwargs:
                                        for tool in i.additional_kwargs['tool_calls']:
                                            text=f"=======工具调用=======  \nindex:{tool['index']}  \nid:{tool['id']}  \n工具类型:{tool['type']}  \n工具名称:{tool[tool['type']]['name']}  \n工具参数:{tool[tool['type']]['arguments']}"
                                            self.other_received.emit(text)
                            if key=='tools':
                                for i in value['messages']:
                                    text=f"=======工具执行结果=======  \n工具名称:{i.name}  \n工具ID:{i.id}  \n工具调用ID:{i.tool_call_id}  \n工具执行结果:  \n{i.content}"
                                    self.other_received.emit(text)
                self.finished.emit()
        except Exception as e:
            # self.chunk_received.emit(f"[ERROR] {str(e)}")
            print(f"[ERROR] {e}")
        finally:
            self.finished.emit()
    def process_request1(self, text, agent):
        # 在QThread中运行异步函数
        asyncio.run(self.async_process_request(text, agent))

    def update_agent(self,agent,kwargs:dict):
        try:
            agent.update(**kwargs)
            self.update_finished.emit()
        except Exception as e:
            self.err_occured.emit(f"[ERROR] {str(e)}")
            self.finished.emit()
        
class ChatBubble(QTextBrowser):
    def __init__(self, text, type:int=0, parent=None):
        super().__init__(parent)
        self.type = type
        # self.setLineWrapMode(QTextEdit.FixedPixelWidth)
        self.setWordWrapMode(QTextOption.WrapAnywhere)
        self.setCursor(Qt.IBeamCursor)
        self.viewport().setCursor(Qt.IBeamCursor)
        if type:
            self.setMarkdown(text)
        else:
            self.setPlainText(text)
        self.setReadOnly(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)  # 仅允许鼠标选择文本（不可拖动）
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setOpenExternalLinks(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        
        # 根据用户或AI设置不同样式
        if type==0:
            #用户消息
            self.setStyleSheet("""
                ChatBubble {
                    background-color: #0066cc;
                    color: white;
                    border-radius: 12px;
                    border-top-right-radius: 0;
                    padding: 5px;
                    font: 15px "Segoe UI";
                }
            """)
            self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        elif type==1:
            # AI消息
            self.setStyleSheet("""
                ChatBubble {
                    background-color: #3b3b3b;
                    color: white;
                    border-radius: 12px;
                    border-top-left-radius: 0;
                    padding: 5px;
                    font: 15px "Segoe UI";
                }
            """)
            self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.typing_timer = QTimer(self)
            self.typing_timer.timeout.connect(self._type_next_char)
            self.pending_text = ""
            self.alltext = ""
        elif type==2:
            #其他消息
            self.setStyleSheet("""
                ChatBubble {
                    background-color: #95EC69;
                    color: black;
                    border-radius: 12px;
                    border-top-left-radius: 0;
                    padding: 5px;
                    font: 15px "Segoe UI";
                }
            """)
            self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        if parent:
            self.scroll_parent=parent
        # 对于QScrollArea，需要监听它的视口(viewport)
            actual_parent = parent.viewport() if isinstance(parent, QScrollArea) else parent
            actual_parent.installEventFilter(self)
            self._parent_to_watch = actual_parent  # 保存引用
        
    def adjust_size(self):
        """根据内容和父窗口大小动态调整尺寸"""
        if not self.parent():
            return

        parent_width = self.parent().width()
        max_width = int(parent_width * 0.8)
        min_width = 40
        # 计算文本需要的宽度
        fm = self.fontMetrics()
        text_width = 0

        # 分别计算每行文本的宽度，取最大值
        for line in self.toPlainText().split('\n'):

            if any(line.startswith(prefix) for prefix in ["![", "[", "```", "    "]):
                line_width = fm.horizontalAdvance(line)+self.contentsMargins().left() + self.contentsMargins().right()+80
            else:
                line_width = fm.horizontalAdvance(line)+self.contentsMargins().left() + self.contentsMargins().right() + 20
            text_width = max(text_width, line_width)
        # 设置合适的宽度（不超过最大宽度）
        ideal_width =max(min_width, min(text_width, max_width))
        #self.setFixedWidth(ideal_width)
        # 计算所需高度
        doc = self.document()
        doc.setDocumentMargin(2)
        doc.setTextWidth(ideal_width - self.contentsMargins().left() - self.contentsMargins().right())
        ideal_height = int(doc.size().height()) + self.contentsMargins().top() + self.contentsMargins().bottom()
        self.setFixedSize(ideal_width,ideal_height)
        # self.setLineWrapColumnOrWidth(ideal_width)
        # 强制重新计算布局
        # self.adjustSize()

    def eventFilter(self, obj, event):
        """监听父窗口大小变化事件"""
        if obj == getattr(self, '_parent_to_watch', None) and event.type() == QEvent.Resize:
            self.adjust_size()
        return super().eventFilter(obj, event)
    
    def resizeEvent(self, event):
        """处理大小变化事件"""
        super().resizeEvent(event)
        self.adjust_size()
    
    def wheelEvent(self, event):
        # 获取父ScrollArea
        scroll_area = self.parent().parent()  # QTextBrowser -> viewport -> QScrollArea
        if isinstance(scroll_area, QScrollArea):
            # 将事件传递给ScrollArea的viewport
            event.setAccepted(False)
            QApplication.sendEvent(scroll_area.viewport(), event)
        else:
            super().wheelEvent(event)

    @Slot(str)
    def append_text(self, new_text):
        """线程安全地添加新文本"""
        self.pending_text += new_text
        if not self.typing_timer.isActive():
             self.typing_timer.start(50)

    def _type_next_char(self):
        """执行打字机效果"""
        if not self.pending_text:
            self.typing_timer.stop()
            self.adjust_size() # Final adjustment
            return
        # 添加一个字符到已显示文本
        self.alltext += self.pending_text[0:3]
        self.setMarkdown(self.alltext)
        self.pending_text = self.pending_text[3:]
        # 自动滚动和调整大小
        if len(self.alltext)%20==0 or not self.pending_text:
            self.adjust_size()
            QTimer.singleShot(10, self.adjust_size)
        elif not self.typing_timer.isActive():
            self.typing_timer.start(30)

class ChatPage(QWidget):
    request_ai_processing = Signal(str, object)
    stop_signal = Signal()
    def __init__(self,agent,parent=None):
        super().__init__(parent)
        self.parent=parent
        self.scroll_area = None  # 添加一个实例变量来存储 QScrollArea
        self._setup_threading()
        self.initUI()
        self.agent=agent
        self.newvcagent=agent.newvcagent()
        self.ai_bubble = None
        
    def _setup_threading(self):
        # 连接信号
        self.request_ai_processing.connect(self.parent.ai_worker.process_request)
        self.stop_signal.connect(self.parent.ai_worker.stop)
        self.parent.ai_worker.chunk_received.connect(self.update_ai_message)
        self.parent.ai_worker.finished.connect(self.on_ai_finished)
        self.parent.ai_worker.other_received.connect(self.on_other_received)
        
    def initUI(self):
        self.setWindowTitle("AI聊天对话框")
        self.resize(600, 800)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        #main_layout.setSpacing(10)
        main_layout.setSpacing(0)

        info_area=QWidget()
        info_layout=QHBoxLayout(info_area)
        info_layout.setSpacing(0)
        info_layout.setContentsMargins(5, 5, 5, 0)
        self.info_new=True
        self.info_button=QPushButton('新对话')
        self.info_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.info_button.setStyleSheet("""
            QPushButton {
                /*border: 1px solid #0099ff;*/
                border-radius: 10px;
                padding: 4px 5px;
                font: 15px "Segoe UI";
            }
            QPushButton:hover {
                background-color: #0099ff;
                color: white;                          
            }
            QPushButton::menu-indicator {
                image: url(:images/resources/icons/drop.svg);                      
                subcontrol-position: right center;    /* 位置 */
                subcontrol-origin: padding;
                width: 15px;  /* 控制图标大小 */
                height: 15px;
                padding-right: 5px;
            }                      
            QPushButton::menu-indicator:hover {
                image: url(:images/resources/icons/drop-white.svg);
                subcontrol-position: right center;    /* 位置 */
                subcontrol-origin: padding;
                width: 15px;  /* 控制图标大小 */
                height: 15px;
                padding-right: 5px;
            }                         
        """)
        
        self.clear_button=QPushButton('清空')
        self.clear_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.clear_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 4px 10px;
                font: 15px "Segoe UI";
            }
            QPushButton:hover {
                background-color: #0099ff;
                color: white;                                                  
            }
        """)
        self.clear_button.clicked.connect(self.on_clear_button_clicked)

        infomenu=QMenu(self.info_button)
        infomenu.setStyleSheet("""
            QMenu {
                border-radius: 10px;
                padding: 5px;
                font: 15px "Segoe UI";
            }
            QMenu::item {
                padding: 8px 8px 8px 10px;
                margin: 2px;
                border-radius: 10px;
            }
            QMenu::item:selected {
                background-color: #0066cc;
            }
""")
        action_group1=QActionGroup(self.info_button)
        action_group1.setExclusive(True)
        action1=infomenu.addAction("对话模式")
        action1.setCheckable(True)
        action_group1.addAction(action1)
        action2=infomenu.addAction("专业模式")
        action2.setCheckable(True)
        action_group1.addAction(action2)
        action1.triggered.connect(lambda: self.on_infomenu_selected(1))
        action2.triggered.connect(lambda: self.on_infomenu_selected(2))
        self.info_button.setMenu(infomenu)
        action1.setChecked(True)
        self.infochoose=1

        info_layout.addWidget(self.info_button,alignment=Qt.AlignLeft)
        info_layout.addWidget(self.clear_button,alignment=Qt.AlignRight)

        main_layout.addWidget(info_area)
        # 创建滚动区域
        self.scroll_area = QScrollArea()  # 将 QScrollArea 保存到实例变量
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 内容容器
        content_widget = QWidget()
        self.chat_layout = QVBoxLayout(content_widget)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(10)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)

        self.scroll_area.setWidget(content_widget)
        main_layout.addWidget(self.scroll_area)
        self.chat_layout.addStretch(1)
        # 输入容器
        input_area = QWidget()
        
        self.input_layout = QHBoxLayout(input_area)
        self.input_layout.setSpacing(0)
        self.input_field =self.set_textedit("输入消息...")
        self.input_field.installEventFilter(self)
        
        self.input_field1=self.set_textedit("输入问题描述……")
        self.input_field1.installEventFilter(self)

        self.input_field2=self.set_textedit("输入模块声明……")
        self.input_field2.installEventFilter(self)

        self.input_field3=self.set_textedit("输入TestBench(注意，本项将直接存储到文件，若填写需确保可直接运行。没有可保持为空)……")
        self.input_field3.installEventFilter(self)

        self.separator=self.create_separator()
        self.separator1=self.create_separator()

        self.send_button = QPushButton("发送")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0099ff;
                color: white;
                border: none;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                padding: 7px 20px;                              
            }
            QPushButton:hover {
                background-color: #0066cc;
                color:#458fda;                          
            }
            QPushButton:disabled {
                background-color: #303030;
                color:#458fda
            }                                  
        """)
        self.send_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        self.menu_button = QToolButton()
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        self.menu_button.setText("▼")
        self.menu_button.setFixedWidth(20)
        self.menu_button.setStyleSheet("""
        QToolButton {
            background-color: #0099ff;
            color: white;
            border: none;
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
            border-top-left-radius: 0px;
            border-bottom-left-radius: 0px;
            padding: 7px 2px;
        }
        QToolButton:hover {
            background-color: #0066cc;
            color: #458fda;
        }
        QToolButton::menu-indicator {
            image: none;  /* 去掉右下角箭头 */
        }
        """)
        self.set_menu_button()
        self.menu_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #0099ff;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 7px 20px;
            }
            QPushButton:hover {
                background-color: #0066cc;
                color:#458fda;                          
            }
            QPushButton:disabled {
                background-color: #303030;
                color:#458fda
            } 
        """)
        self.cancel_button.clicked.connect(self.on_cancel_button_clicked)
        self.cancel_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        send_area = QWidget()
        send_layout = QHBoxLayout(send_area)
        send_layout.setSpacing(0)
        send_layout.setContentsMargins(0, 0, 0, 0)
        send_layout.addWidget(self.send_button)
        send_layout.addWidget(self.menu_button)

        button_area=QWidget()
        button_layout = QHBoxLayout(button_area)
        button_layout.addStretch()
        button_layout.addWidget(send_area)
        button_layout.addWidget(self.cancel_button)

        self.input_layout.addWidget(self.input_field)
        
        # self.send_button.clicked.connect(lambda: self.add_message(self.input_field.toPlainText(), True))
        self.send_button.clicked.connect(lambda: self.send_message())
        # self.send_button.resize(100,40)
        # self.menu_button.resize(20,40)
        # self.cancel_button.resize(100,40)
        
        main_layout.addWidget(input_area)
        main_layout.addWidget(button_area)

        # 添加示例对话
        # self.add_message("你好！我是AI助手，有什么可以帮您的吗？", False)

    def create_separator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setLineWidth(1)
        return separator
    
    def on_infomenu_selected(self, index):
        if index == self.infochoose:
            return
        elif index == 1:
            self.infochoose=1
            self.remove_all_widgets(self.input_layout)
            self.input_layout.addWidget(self.input_field)
        elif index == 2:
            self.infochoose=2
            self.remove_all_widgets(self.input_layout)
            self.input_layout.addWidget(self.input_field1)
            if self.typechoose==2:
                self.input_layout.addWidget(self.separator)
                self.input_layout.addWidget(self.input_field2)
                self.input_layout.addWidget(self.separator1)
                self.input_layout.addWidget(self.input_field3)
    
    def on_clear_button_clicked(self):
        self.input_field.clear()
        self.input_field1.clear()
        self.input_field2.clear()
        self.input_field3.clear()

        self.newvcagent=self.agent.newvcagent(newmemory=True)

        self.info_new=True
        self.info_button.setText("新对话")
        self.clear_all_widgets(self.chat_layout)
        self.chat_layout.addStretch(1)
    
    def clear_all_widgets(self,layout):
        # 遍历并删除所有子控件
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()  # 安全删除控件
    
    def remove_all_widgets(self,layout):
        for i in reversed(range(layout.count())):
            item = layout.takeAt(i)  # 从 layout 里取出
            widget = item.widget()
            if widget is not None:
                layout.removeWidget(widget)  # 从 layout 移除
                widget.setParent(None) 
    
    def set_menu_button(self):
        self.menu = QMenu(self.menu_button)
        self.menu.setStyleSheet("""
            QMenu {
                border-radius: 10px;
                padding: 5px;
                font: 12px "Segoe UI";
            }
            QMenu::item {
                padding: 8px 8px 8px 10px;
                margin: 2px;
                border-radius: 10px;
            }
            QMenu::item:selected {
                background-color: #0066cc;
            }
""")
        self.action_group=QActionGroup(self.menu_button)
        self.action_group.setExclusive(True)
        action1=self.menu.addAction("物理C++")
        action1.setCheckable(True)
        self.action_group.addAction(action1)
        action2=self.menu.addAction("电路设计Verilog")
        action2.setCheckable(True)
        self.action_group.addAction(action2)
        action1.triggered.connect(lambda: self.on_menu_selected(1))
        action2.triggered.connect(lambda: self.on_menu_selected(2))
        action2.setChecked(True)
        self.typechoose=2
        self.menu_button.setMenu(self.menu)
    
    def on_menu_selected(self, a:int):
        if a==self.typechoose:
            return
        self.typechoose=a
        if a==1:
            self.newvcagent=self.agent.newvcagent(TYPE='c++')
            if self.infochoose==2:
                self.remove_all_widgets(self.input_layout)
                self.input_layout.addWidget(self.input_field1)
        elif a==2:
            self.newvcagent=self.agent.newvcagent(TYPE='verilog')
            if self.infochoose==2:
                self.remove_all_widgets(self.input_layout)
                self.input_layout.addWidget(self.input_field1)
                self.input_layout.addWidget(self.separator)
                self.input_layout.addWidget(self.input_field2)
                self.input_layout.addWidget(self.separator1)
                self.input_layout.addWidget(self.input_field3)

    def on_cancel_button_clicked(self):
        # if self.parent.worker_thread.isRunning():
        #     self.parent.worker_thread.quit()
        # if not self.parent.worker_thread.wait(3000): # Wait up to 3 seconds
        #     self.parent.worker_thread.terminate()
        #     self.parent.worker_thread.wait()
        # self.stop_signal.emit()
        # self.agent.memory.reset({"configurable": {"thread_id": 1},"recursion_limit": 50})
        self.input_field.clear()
        self.input_field.clear()
        self.input_field1.clear()
        self.input_field2.clear()
        self.input_field3.clear()
        # self.info_button.setText(self.infotext)
        # self.send_button.setEnabled(True)

    def set_textedit(self,holder:str):
        a= QTextEdit()
        a.setMinimumHeight(80)
        a.setMaximumHeight(160)
        a.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        a.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                /*border: 1px solid #ccc;*/
                font: 14px "Segoe UI";
                border-radius: 10px;
                padding: 10px;
            }
        """)
        a.setPlaceholderText(holder)
        return a
    
    def eventFilter(self, obj, event):
        # Enter发送消息
        if obj in (self.input_field,self.input_field1,self.input_field2) and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if QApplication.keyboardModifiers() & Qt.ShiftModifier:
                    return False 
                else:
                    self.send_message()
                    return True
        return super().eventFilter(obj, event)

    def add_message(self, text, type:int=0):
        self.input_field.clear()  # 清空输入框
        text.strip()  # 去除首尾空格
        if not text:
            return  # 如果文本为空，则不添加消息
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        layout = QHBoxLayout(container)
        
        bubble = ChatBubble(text,type,self.scroll_area)
        
        bubble.adjust_size()  # 调整气泡大小
        # 根据消息来源设置对齐方式
        if not type:
            #用户
            layout.setContentsMargins(0, 0, 5, 2)
            layout.addStretch()
            layout.addWidget(bubble)
            #bubble.setParent(self.layout)
        else:
            #非用户
            layout.setContentsMargins(5, 0, 0, 2)
            layout.addWidget(bubble)
            layout.addStretch()
        # if self.chat_layout.count() >= 1:
        
        self.chat_layout.insertWidget(self.chat_layout.count() - 1,container)
        # else:
        # self.chat_layout.addWidget(container)
        if self.scroll_area:
            QTimer.singleShot(500, lambda:self.scroll_area.ensureWidgetVisible(bubble))    

    def send_message(self):
        if self.send_button.isEnabled()==False:
            return
        # 获取输入框中的文本并添加到聊天框中
        if self.infochoose==1:#聊天模式
            text=self.input_field.toPlainText().strip()
            if not text:
                return  # 如果文本为空，则不添加消息
            
            self.agent.QUESTION=text

            if self.info_new:
                    self.info_new=False
                    self.infotext=text[:6]
            self.input_field.clear()  # 清空输入框          
        if self.infochoose==2:#专业模式
            if self.typechoose==1:
                text=self.input_field1.toPlainText().strip()
                if not text:
                    return  # 如果文本为空，则不添加消息
                
                if self.info_new:
                        self.info_new=False
                        self.infotext=text[:6]
                self.input_field1.clear()
                text="根据以下描述生成C++代码以解决物理问题,确保最后用finalout工具给出没有任何error甚至warning的代码.\n问题描述:\n"+text

                self.agent.QUESTION=text

            if self.typechoose==2:
                text1=self.input_field1.toPlainText().strip()
                text2=self.input_field2.toPlainText().strip()
                text3=self.input_field3.toPlainText().strip()
                if not text1 and not text2:
                    return
                if self.info_new:
                    self.info_new=False
                    self.infotext=text1[:18]
                self.input_field1.clear()

                self.agent.QUESTION=text1

                if text2:
                    self.agent.MODULE=text2

                    self.input_field2.clear()
                    text2="\n模块设计:\n"+text2
                text="根据以下描述完成verilog模块设计,确保最后用finalout工具给出没有任何error甚至warning的代码。除非特殊情况,均假定clock/clk正边沿触发\n问题描述:\n"+text1+text2

                if text3:
                    self.agent.TESTBENCH=text3

                    self.input_field3.clear()
                    text3="\n用户已存入testbench,无需调用工具生成"
        
        self.info_button.setText("AI 正在回复...")
        self.send_button.setEnabled(False)
        self._create_user_bubble(text)
        self.request_ai_processing.emit(text, self.newvcagent)
        # if self.scroll_area:
        #     QTimer.singleShot(51, lambda: self.ai_worker.process_request(text,self.newvcagent))
            # QTimer.singleShot(51,lambda:self.stream_ai_response(text))
    @Slot(str)
    def update_ai_message(self, chunk):
        """线程安全的UI更新"""
        if  self.ai_bubble is None:
            self.ai_bubble = self._create_ai_bubble()
        # 使用QueuedConnection确保线程安全
        # self.ai_bubble.append_text(chunk)  # 逐步追加文本
        QMetaObject.invokeMethod(
            self.ai_bubble,
            "append_text",
            Qt.QueuedConnection,
            Q_ARG(str, chunk)
        )

    def on_other_received(self,text):
        self.ai_bubble = None
        other_bubble = self._create_other_bubble(text)

    @Slot()
    def on_ai_finished(self):
        """清理线程资源"""
        self.ai_bubble = None
        self.send_button.setEnabled(True)
        self.info_button.setText(self.infotext)

    def _create_user_bubble(self, text):
        """创建用户消息气泡"""
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        layout = QHBoxLayout(container)
        
        bubble = ChatBubble(text,0,self.scroll_area)
        bubble.adjust_size()
        
        layout.setContentsMargins(0, 0, 5, 2)
        layout.addStretch()
        layout.addWidget(bubble)
        
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, container)
        
        # 确保滚动到新消息
        if self.scroll_area:
            QTimer.singleShot(50, lambda: self.scroll_area.ensureWidgetVisible(bubble))
    def _create_ai_bubble(self):
        ai_bubble = ChatBubble("",1,self.scroll_area)
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        layout = QHBoxLayout(container)
        layout.addWidget(ai_bubble)
        layout.addStretch()
        self.chat_layout.insertWidget(self.chat_layout.count() - 1,container)
        # 确保界面立即更新
        #QApplication.processEvents()
        return ai_bubble

    def _create_other_bubble(self,text):
        other_bubble = ChatBubble(text,2,self.scroll_area)
        container = QWidget()
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        layout = QHBoxLayout(container)
        layout.addWidget(other_bubble)
        layout.addStretch()
        self.chat_layout.insertWidget(self.chat_layout.count() - 1,container)
    def closeEvent(self, event):
        super().closeEvent(event)

class SettingsPage(QWidget):
    update_agent=Signal(object,dict)
    def __init__(self,accountmanager,agent,currentcount:dict,parent=None):
        super().__init__(parent)
        self.set_area=QWidget(self)
        layout = QGridLayout(self)
        self.set_area.setLayout(layout)
        self.setWindowTitle("设置")
        self.currentcount=currentcount
        self.agent=agent
        self.accountmanager=accountmanager

        label_1=QLabel("模型类别:")
        self.combo_1=QComboBox(self)
        self.combo_1.setEditable(True)
        self.combo_1.addItems(['deepseek','qwen','siliconflow'])
        self.combo_1.setCurrentIndex(-1)
        self.combo_1.currentIndexChanged.connect(self.on_combo_1_changed)
        label_2=QLabel("模型名称:")
        self.combo_2=QComboBox(self)
        self.combo_2.addItem('请先选择模型类别!')
        self.combo_2.setEditable(True)
        label_style="""
            QLabel { 
                color: None; 
                font: 15px "Segoe UI";
                font-weight: bold;
                }"""

        label_1.setStyleSheet(label_style)
        label_2.setStyleSheet(label_style)
        combo_style=f"""
            QComboBox {{
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 1px 2px 1px 2px;
                min-width: 6em;
                font: 15px "Segoe UI";
            }}
            QComboBox:hover {{
                border: 1px solid #0099ff;
            }}
            /*QCombobox右侧按钮*/
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;/*放于右方顶部*/
                width: 30px;/*设置按钮范围宽度*/
                border-top-right-radius: 3px;/*设置边框圆角*/
                border-bottom-right-radius: 3px;
                /*padding-right: 50px;*/
            }}
            QComboBox::down-arrow {{
                image: url(:/images/resources/icons/drop.svg);
                width: 24px;/*设置该图标的宽高*/
                height: 24px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #0099ff;
                border-radius: 10px;
                outline:0px;
                padding: 2px;}}
            QComboBox QAbstractItemView::item {{
                
                font: 15px "Segoe UI";
                height: 36px;   /* 项的高度（设置pComboBox->setView(new QListView());后，该项才起作用） */
                border:none;
                background-color: none;
            }}
            QComboBox QAbstractItemView::item:last-child {{
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                border-bottom: none;
            }}
            QComboBox QAbstractItemView::item:hover {{
                color: white;
                /* 整个下拉窗体越过每项的背景色 */
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            /* 下拉后，整个下拉窗体被选择的每项的样式 */
            QComboBox QAbstractItemView::item:selected {{
                color: white;
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            """
        self.combo_1.setStyleSheet(combo_style)
        self.combo_2.setStyleSheet(combo_style)

        label_3=QLabel("Apikey:")
        self.line_3=QLineEdit(self)
        self.line_3.setPlaceholderText("请输入您对应模型的apikey")
        self.line_3.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_3.setClearButtonEnabled(True)
        label_4=QLabel("Tavilykey:")
        self.line_4=QLineEdit(self)
        self.line_4.setPlaceholderText("搜索引擎工具key,没有留空即可")
        self.line_4.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_4.setClearButtonEnabled(True)
        
        label_3.setStyleSheet(label_style)
        label_4.setStyleSheet(label_style)
        line_style="""
            QLineEdit {
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QLineEdit:hover {
                background-color: #0099ff;
                color:white;                          
            }
            QLineEdit:focus {
                background-color: #0099ff;
                color:white;
            }
                """
        self.line_3.setStyleSheet(line_style)
        self.line_4.setStyleSheet(line_style)
        
        save_area = QWidget()
        self.save_button = QPushButton("保存")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #0099ff;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #0066cc;
                color:#458fda;                          
            }
            QPushButton:disabled {
                        background-color: #303030;
                        color:#458fda
                    } 
        """)
        save_layout = QHBoxLayout(save_area)
        save_layout.addStretch()
        save_layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.on_save_button_clicked)

        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(3, 1)

        layout.addWidget(label_1,0,0)
        layout.addWidget(self.combo_1,0,1)
        layout.addWidget(label_2,0,2)
        layout.addWidget(self.combo_2,0,3)
        layout.addWidget(label_3,1,0)
        layout.addWidget(self.line_3,1,1,1,3)
        layout.addWidget(label_4,2,0)
        layout.addWidget(self.line_4,2,1,1,3)
        mainlayout = QVBoxLayout(self)
        self.setLayout(mainlayout)
        mainlayout.addWidget(self.set_area)
        mainlayout.addWidget(save_area)
        self._setup_threading()
        self.update_text()
        
    def update_text(self):
        self.modeltype=self.currentcount['modeltype']
        self.combo_1.setCurrentText(self.modeltype)
        self.combo_2.setCurrentText(self.currentcount['modelname'])
        self.line_3.setText(self.currentcount['apikey'])
        self.line_4.setText(self.currentcount['Tavilykey'])

    def _setup_threading(self):
        self.update_agent.connect(self.parent().ai_worker.update_agent)
        self.parent().ai_worker.update_finished.connect(self.on_update_finished)

    @Slot(int)
    def on_combo_1_changed(self, index):
        if index == 0:
            self.combo_2.clear()
            self.combo_2.addItems(['deepseek-chat','deepseek-reasoner'])
        elif index == 1:
            self.combo_2.clear()
            self.combo_2.addItems(["qwen-turbo", "qwq-plus","qwen-plus"])
        elif index == 2:
            self.combo_2.clear()
            self.combo_2.addItems(["Qwen/Qwen2.5-72B-Instruct-128K", "Qwen/QwQ-32B"])

    @Slot()
    def on_save_button_clicked(self):
        self.save_button.setEnabled(False)
        if not self.line_3.text() or not self.combo_1.currentText() or not self.combo_2.currentText():
            QMessageBox.warning(self, "警告", "请确保modeltype,modelname,apikey全部填写")
            return
        keywards={'modeltype':self.combo_1.currentText(),'modelname':self.combo_2.currentText(),'apikey':self.line_3.text(),'Tavilykey':self.line_4.text()}
        updatekeywords={'modelname':self.combo_2.currentText(),'apikey':self.line_3.text(),'Tavilykey':self.line_4.text()}
        try:
            self.accountmanager.update_account_pro(modeltype=self.combo_1.currentText(),**updatekeywords)
        except Exception as e:
            QMessageBox.warning(self, "写入数据库错误", str(e))

        self.update_agent.emit(self.agent,keywards)

    def on_update_finished(self):
        self.update_text()
        QMessageBox.information(self, "保存成功", "保存成功")
        self.save_button.setEnabled(True)

class AboutPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setWindowTitle("关于")
        label = QLabel("关于页面")
        anounce=r"""
    ███╗   ██╗███████╗██╗    ██╗██╗   ██╗ ██████╗
    ████╗  ██║██╔════╝██║    ██║██║   ██║██╔════╝
    ██╔██╗ ██║█████╗  ██║ █╗ ██║██║   ██║██║     
    ██║╚██╗██║██╔══╝  ██║███╗██║╚██╗ ██╔╝██║     
    ██║ ╚████║███████╗╚███╔███╔╝ ╚████╔╝ ╚██████╗
    ╚═╝  ╚═══╝╚══════╝ ╚══╝╚══╝   ╚═══╝   ╚═════╝

    """
        label1 = QLabel(self)
        label1.setPixmap(QPixmap(':/images/resources/icons/ouricon.svg'))
        label2 = QLabel("正在使用的是中国东南大学2025届学生毕业设计成果\n这是由LLM驱动的Verilog与c++代码自动生成及处理系统\n软件界面部分基于Pyside6开发,底层交互部分基于langchain,langraph框架开发。\n有关本软件更多信息,联系邮箱:213210411@seu.edu.cn\n欢迎交流讨论!!!")
        label_style="""
            QLabel { 
                color: None; 
                font: 18px "Segoe UI";
                font-weight: bold;
                }"""
        label.setStyleSheet(label_style)
        label1.setStyleSheet(label_style)
        label2.setStyleSheet(label_style)
        label.setAlignment(Qt.AlignCenter)
        label1.setAlignment(Qt.AlignCenter)
        label2.setAlignment(Qt.AlignCenter)
        layout.addWidget(label,0)
        layout.addWidget(label1,2)
        layout.addWidget(label2,1)

class LogPage(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.setWindowTitle("日志")

        label = QLabel("运行日志")
        label.setStyleSheet("font-size: 20px;")
        label.setAlignment(Qt.AlignCenter)

        self.log_text = QTextBrowser(self)
        self.log_text.setStyleSheet("""
                QTextBrowser {
                    border-radius: 12px;
                    padding: 5px;
                    font: 14px "Segoe UI";
                }
            """)
        layout.addWidget(label)
        layout.addWidget(self.log_text)

        self.parent().ai_worker.log_received.connect(self.append_log)
    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.ensureCursorVisible()

class AnimatedNavButton(QPushButton):
    def __init__(self, icon_path, text="",parent=None):
        super().__init__(text, parent)
        self._icon_path = icon_path
        self._icon_size = QSize(24, 24)
        self._hover_icon_size = QSize(32, 32)
        self._text = text
        self.setIcon(QIcon(self._icon_path))
        # 初始状态只显示图标
        self.update_button(show_text=False)
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 图标放大动画
        self.icon_animation = QPropertyAnimation(self, b"iconSize")
        self.icon_animation.setDuration(200)
        self.icon_animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def get_icon_size(self):
        return self._icon_size
    
    def set_icon_size(self, size):
        self._icon_size = size
        self.setIconSize(size)
    
    iconSize = Property(QSize, get_icon_size, set_icon_size)
    
    def update_button(self, show_text):
        """更新按钮显示状态"""
        if show_text:
            self.setText(self._text) 
        else:
            self.setText("")  # 隐藏文本
        self.setIconSize(self._icon_size)
    
    def enterEvent(self, event):
        """鼠标进入事件 - 显示文本并放大图标"""
        #self.update_button(show_text=True)
        self.icon_animation.stop()
        self.icon_animation.setStartValue(self.iconSize)  # 注意这里去掉了括号
        self.icon_animation.setEndValue(self._hover_icon_size)
        self.icon_animation.start()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开事件 - 隐藏文本并恢复图标大小"""
        #if not self.isChecked():  # 如果按钮不是选中状态才隐藏文本
            #self.update_button(show_text=False)
        self.icon_animation.stop()
        self.icon_animation.setStartValue(self.iconSize)
        self.icon_animation.setEndValue(self._icon_size)
        self.icon_animation.start()
        super().leaveEvent(event)

class NavWidget(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self._collapsed_width = 64
        self._expanded_width = 160
        self.setFixedWidth(self._collapsed_width)
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setContentsMargins(7, 5, 7, 10)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)
        self.buttons = []
        self.animation = QPropertyAnimation(self, b"minimumWidth")
        self.animation.setDuration(300)
        self.setMouseTracking(True)
        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True) 
        self._leave_timer.timeout.connect(lambda: self._handle_hover(False))
              
    def addButton(self, button:AnimatedNavButton):
        self.buttons.append(button)
        self.layout.addWidget(button)
        
    def addAvator(self, button:QPushButton):
        self.avator=button
        self.layout.addWidget(button)
        self.avator.setIconSize(QSize(32, 32))
        self.avator_animation = QPropertyAnimation(self.avator, b"iconSize")
        self.avator_animation.setDuration(300)
        self.avator_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.avator_e=QSize(72,72)
        self.avator_f=QSize(32,32)

    def _handle_hover(self, is_hover):
        self.animation.stop()
        target_width = self._expanded_width if is_hover else self._collapsed_width
        self.animation.setStartValue(self.width())
        self.animation.setEndValue(target_width)
        self.animation.start()
        
        if self.avator:
            self.avator_animation.stop()
            size = self.avator_e if is_hover else self.avator_f
            self.avator_animation.setEndValue(size)
            self.avator_animation.start()
            
        for button in self.buttons:
            if button:
                button.update_button(is_hover)

    def enterEvent(self, event):
        self._handle_hover(True)
        if self._leave_timer.isActive():
            self._leave_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._leave_timer.start(500)
        super().leaveEvent(event)

    def clear(self):
        """清空所有按钮"""
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons.clear()

class CircleImageLabel(QLabel):
    def __init__(self, img_path:str='', size=300,realsize=300):
        super().__init__()
        self.setFixedSize(size, size)  # 固定大小
        self.setScaledContents(True)
        self.realsize=realsize
        if img_path:
            self.setPixmap(img_path)

    def get_circle_pixmap(self, img_path):
        pixmap = QPixmap(img_path).scaled(
            self.realsize, self.realsize,
            Qt.KeepAspectRatioByExpanding,  # 填充满
            Qt.SmoothTransformation
        )

        mask = QPixmap(self.realsize,self.realsize)
        mask.fill(Qt.transparent)

        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, self.realsize, self.realsize)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        return mask

    def setPixmap(self, img_path):
        super().setPixmap(self.get_circle_pixmap(img_path))

class RegisterPage(QWidget):
    run=Signal(dict)
    def __init__(self,account_manager,parent=None,showmessage=False):
        super().__init__(parent)
        self.setWindowTitle("新用户")
        self.resize(360, 430)
        self.setFixedWidth(360)
        self.setMaximumHeight(560)
        self.setContentsMargins(15,15,5,15)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint|Qt.WindowType.WindowStaysOnTopHint|self.windowFlags() | Qt.WindowType.Window)
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # self.setStyleSheet("""
        #     QDialog {
        #         border-radius: 10px;
        #         background: none;
        #     }
        # """)
        self.success=None
        self.account_manager=account_manager
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        self.setWindowIcon(QIcon(':/images/resources/icons/ouricon.svg'))
        
        label=QLabel(self)
        label.setPixmap(QPixmap(':/images/resources/icons/ouricon.svg'))
        label.setFixedSize(230,120)
        label.setScaledContents(True)

        self.set_area()

        #勾选区域
        check_area=QWidget()
        cheack_layout=QHBoxLayout(check_area)
        # 记住API Key
        self.remember_check = QCheckBox("记住API Key")
        # 自动登录
        self.auto_login_check = QCheckBox("自动登录")
        cheack_layout.addWidget(self.remember_check)
        cheack_layout.addWidget(self.auto_login_check)

        # 运行按钮
        run_button=QPushButton("开始使用",self)
        btn_style="""
    QPushButton {
        background-color: #0099ff;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
    }
    QPushButton:hover {
        background-color: #0066cc;
        color:#458fda;                          
    }
"""
        run_button.setStyleSheet(btn_style)
        main_layout.setSpacing(15)
        main_layout.addWidget(label,0,alignment=Qt.AlignCenter)
        main_layout.addWidget(self.set_area,1)
        main_layout.addWidget(check_area,0)
        main_layout.addWidget(run_button,0)
        if showmessage:
            QMessageBox.information(
                    self,
                    "提示",
                    "首次使用须知:\n要使用本软件需要确保:\n1.C++:已安装g++编译软件并配置好环境(推荐MinGW)\n2.verilog:已安装iverilog编译软件并配置好环境"
                )
        run_button.clicked.connect(lambda:self.on_run_button_clicked())

    def set_area(self):
        self.set_area = QWidget()
        self.layout = QFormLayout(self.set_area)
        label_1=QLabel("模型类别:")
        self.combo_1=QComboBox(self)
        self.combo_1.setEditable(True)
        self.combo_1.addItems(['deepseek','qwen','siliconflow'])
        self.combo_1.setCurrentIndex(-1)
        self.combo_1.currentIndexChanged.connect(self.on_combo_1_changed)
        self.combo_1.lineEdit().editingFinished.connect(self.on_combo_1_edited)
        self.combo_1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label_2=QLabel("模型名称:")
        self.combo_2=QComboBox(self)
        self.combo_2.addItem('请先选择模型类别!')
        self.combo_2.setEditable(True)
        self.combo_2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label_style="""
            QLabel { 
                color: None; 
                font: 15px "Segoe UI";
                font-weight: bold;
                }"""

        label_1.setStyleSheet(label_style)
        label_2.setStyleSheet(label_style)
        combo_style=f"""
            QComboBox {{
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 1px 2px 1px 2px;
                min-width: 6em;
                font: 15px "Segoe UI";
            }}
            QComboBox:hover {{
                border: 1px solid #0099ff;
            }}
            /*QCombobox右侧按钮*/
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;/*放于右方顶部*/
                width: 30px;/*设置按钮范围宽度*/
                border-top-right-radius: 3px;/*设置边框圆角*/
                border-bottom-right-radius: 3px;
                /*padding-right: 50px;*/
            }}
            QComboBox::down-arrow {{
                image: url(:/images/resources/icons/drop.svg);
                width: 24px;/*设置该图标的宽高*/
                height: 24px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #0099ff;
                border-radius: 10px;
                outline:0px;
                padding: 2px;}}
            QComboBox QAbstractItemView::item {{
                
                font: 15px "Segoe UI";
                height: 36px;   /* 项的高度（设置pComboBox->setView(new QListView());后，该项才起作用） */
                border:none;
                background-color: none;
            }}
            QComboBox QAbstractItemView::item:last-child {{
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                border-bottom: none;
            }}
            QComboBox QAbstractItemView::item:hover {{
                color: white;
                /* 整个下拉窗体越过每项的背景色 */
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            /* 下拉后，整个下拉窗体被选择的每项的样式 */
            QComboBox QAbstractItemView::item:selected {{
                color: white;
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            """
        self.combo_1.setStyleSheet(combo_style)
        self.combo_2.setStyleSheet(combo_style)

        label_3=QLabel("Apikey:")
        self.line_3=QLineEdit(self)
        self.line_3.setPlaceholderText("请输入您对应模型的apikey")
        self.line_3.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_3.setClearButtonEnabled(True)
        self.line_3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label_4=QLabel("Tavilykey:")
        self.line_4=QLineEdit(self)
        self.line_4.setPlaceholderText("搜索引擎工具key,没有留空即可")
        self.line_4.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_4.setClearButtonEnabled(True)
        self.line_4.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        label_3.setStyleSheet(label_style)
        label_4.setStyleSheet(label_style)
        line_style="""
            QLineEdit {
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QLineEdit:hover {
                background-color: #0099ff;
                color:white;                          
            }
            QLineEdit:focus {
                background-color: #0099ff;
                color:white;
            }
                """
        self.line_3.setStyleSheet(line_style)
        self.line_4.setStyleSheet(line_style)
        
        self.label_5=QLabel("Api_Base:")
        self.line_5=QLineEdit()
        self.line_5.setPlaceholderText("请输入自定义模型的baseurl")
        self.label_5.setStyleSheet(label_style)
        self.line_5.setStyleSheet(line_style)
        self.line_5.setClearButtonEnabled(True)
        self.line_5.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.layout.addRow(label_1, self.combo_1)
        self.layout.addRow(label_2, self.combo_2)
        self.layout.addRow(label_3, self.line_3)
        self.layout.addRow(label_4, self.line_4)
        self.set_area.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)

    @Slot(int)
    def on_combo_1_changed(self, index):
        if index == 0:
            self.combo_2.clear()
            self.combo_2.addItems(['deepseek-chat','deepseek-reasoner'])
        elif index == 1:
            self.combo_2.clear()
            self.combo_2.addItems(["qwen-turbo", "qwq-plus","qwen-plus"])
        elif index == 2:
            self.combo_2.clear()
            self.combo_2.addItems(["Qwen/Qwen2.5-72B-Instruct-128K", "Qwen/QwQ-32B"])
        if self.layout.rowCount()==5:
            item=self.layout.takeRow(3)
            self.label_5.hide()
            self.line_5.hide()  
                
    def on_combo_1_edited(self):
        text=self.combo_1.currentText()
        if text not in [self.combo_1.itemText(i) for i in range(self.combo_1.count())] and text:
            self.combo_2.clear()
            self.combo_2.setPlaceholderText("输入自定义模型名称")
            self.label_5.show()
            self.line_5.show()
            self.layout.insertRow(3,self.label_5, self.line_5)
    
    def on_run_button_clicked(self):
        modeltype=self.combo_1.currentText()
        modelname=self.combo_2.currentText()
        apikey=self.line_3.text()
        tavilykey=self.line_4.text()
        api_base=self.line_5.text()
        if not all([modeltype,modelname,apikey]):
            QMessageBox.warning(self, "警告", "请填写完整信息！")
            return
        keywards={'modeltype':modeltype,'modelname':modelname,'apikey':apikey,'Tavilykey':tavilykey}
        if api_base:
            keywards['api_base']=api_base
        try:
            if self.remember_check.isChecked():
                self.success = self.account_manager.add_account(
                    modeltype=modeltype,
                    modelname=modelname,
                    apikey=apikey,
                    tavilykey=tavilykey,
                    remember_apikey=self.remember_check.isChecked(),
                    auto_login=self.auto_login_check.isChecked(),
                    avatar_path=':images/resources/icons/person.png',
                    api_base=api_base
                )
            else:
                self.success = self.account_manager.add_account(
                    modeltype=modeltype,
                    modelname=modelname,
                    apikey=None,
                    tavilykey=None,
                    remember_apikey=self.remember_check.isChecked(),
                    auto_login=self.auto_login_check.isChecked(),
                    avatar_path=':images/resources/icons/person.png',
                    api_base=api_base
                )
        except Exception as e:
            QMessageBox.warning(self, "警告", f"[ERROR]{e}")
        if not self.success:
            result=QMessageBox.critical(self, "警告", "该模型账户已存在！是否选择覆盖原账号",QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Ok)
            if result==QMessageBox.StandardButton.Ok:
                self.account_manager.update_account_pro(**keywards)
            else:
                return
        self.run.emit(keywards)

class FirstPage(QWidget):
    """账户登录页面"""
    login_run=Signal(dict,str)
    open_register_run=Signal()
    request_quit=Signal()
    def __init__(self, account_manager, parent=None):
        super().__init__(parent)
        self.account_manager = account_manager
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("登入")
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowMinimizeButtonHint | # 最小化按钮
            Qt.WindowCloseButtonHint      # 关闭按钮
            |Qt.WindowType.WindowStaysOnTopHint
        )
        
        self.setWindowIcon(QIcon(':/images/resources/icons/ouricon.png'))
        self.resize(320, 400)
        self.setMaximumSize(360,560)
        self.setContentsMargins(15, 0, 15, 0)

        layout = QVBoxLayout(self)
        
        # 头像预览
        self.avatar_label = CircleImageLabel(size=100)
        
        #勾选区域
        check_area=QWidget()
        cheack_layout=QHBoxLayout(check_area)
        
        # 记住API Key
        self.remember_check = QCheckBox("记住API Key")
        
        # 自动登录
        self.auto_login_check = QCheckBox("自动登录")
        cheack_layout.addWidget(self.remember_check)
        cheack_layout.addWidget(self.auto_login_check)

        # 账户列表
        self.set_area()
        self.account_combo.currentIndexChanged.connect(self.update_account_preview)
        self.refresh_accounts()

        # 按钮
        btn_style="""
            QPushButton {
                background-color: #0099ff;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #0066cc;
                color:#458fda;                          
            }
                """
        
        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("进入")
        self.login_btn.setStyleSheet(btn_style)
        self.login_btn.clicked.connect(self.login)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color:#ff6d1f ;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #FF5765;
                color:white;                          
            }
                """)
        self.delete_btn.clicked.connect(self.on_delete_btn_clicked)

        btn_layout.addWidget(self.delete_btn,1)
        btn_layout.addWidget(self.login_btn,3)

        self.register_btn = QPushButton("新账户")
        self.register_btn.setStyleSheet(btn_style)
        self.register_btn.clicked.connect(lambda:self.open_register_run.emit())
        
        layout.addWidget(self.avatar_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.set_area)
        layout.addWidget(check_area)
        layout.addWidget(self.register_btn)
        layout.addLayout(btn_layout)
  
    def set_area(self):
        self.set_area = QWidget()
        self.layout = QFormLayout(self.set_area)
        label_1=QLabel("模型:")
        self.account_combo=QComboBox(self)
        self.account_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        label_style="""
            QLabel { 
                color: None; 
                font: 15px "Segoe UI";
                font-weight: bold;
                }"""

        label_1.setStyleSheet(label_style)
        combo_style=f"""
            QComboBox {{
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 1px 2px 1px 2px;
                min-width: 6em;
                font: 15px "Segoe UI";
            }}
            QComboBox:hover {{
                border: 1px solid #0099ff;
            }}
            /*QCombobox右侧按钮*/
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;/*放于右方顶部*/
                width: 30px;/*设置按钮范围宽度*/
                border-top-right-radius: 3px;/*设置边框圆角*/
                border-bottom-right-radius: 3px;
                /*padding-right: 50px;*/
            }}
            QComboBox::down-arrow {{
                image: url(:/images/resources/icons/drop.svg);
                width: 24px;/*设置该图标的宽高*/
                height: 24px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #0099ff;
                border-radius: 10px;
                outline:0px;
                padding: 2px;}}
            QComboBox QAbstractItemView::item {{
                
                font: 15px "Segoe UI";
                height: 36px;   /* 项的高度（设置pComboBox->setView(new QListView());后，该项才起作用） */
                border:none;
                background-color: none;
            }}
            QComboBox QAbstractItemView::item:last-child {{
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                border-bottom: none;
            }}
            QComboBox QAbstractItemView::item:hover {{
                color: white;
                /* 整个下拉窗体越过每项的背景色 */
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            /* 下拉后，整个下拉窗体被选择的每项的样式 */
            QComboBox QAbstractItemView::item:selected {{
                color: white;
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            """
        self.account_combo.setStyleSheet(combo_style)

        label_3=QLabel("Apikey:")
        self.line_3=QLineEdit(self)
        self.line_3.setPlaceholderText("请输入您对应模型的apikey")
        self.line_3.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_3.setClearButtonEnabled(True)
        self.line_3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label_4=QLabel("Tavilykey:")
        self.line_4=QLineEdit(self)
        self.line_4.setPlaceholderText("搜索引擎工具key,没有留空即可")
        self.line_4.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_4.setClearButtonEnabled(True)
        self.line_4.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        label_3.setStyleSheet(label_style)
        label_4.setStyleSheet(label_style)
        line_style="""
            QLineEdit {
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QLineEdit:hover {
                background-color: #0099ff;
                color:white;                          
            }
            QLineEdit:focus {
                background-color: #0099ff;
                color:white;
            }
                """
        self.line_3.setStyleSheet(line_style)
        self.line_4.setStyleSheet(line_style)
        
        self.layout.addRow(label_1, self.account_combo)
        self.layout.addRow(label_3, self.line_3)
        self.layout.addRow(label_4, self.line_4)
        self.set_area.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)

    def refresh_accounts(self):
        """刷新账户列表"""
        self.account_combo.clear()
        accounts = self.account_manager.get_accounts()
        i=0
        for acc in accounts:
            item = f"{acc[1]} - {acc[2]}"
            self.account_combo.addItem(item,userData=acc[0])
            if acc[3]:
                self.account_combo.setCurrentIndex(i)
            i=i+1
    
    def update_account_preview(self, current):
        """更新账户预览信息"""
        account_id = self.account_combo.itemData(current)
        details = self.account_manager.get_account_details(account_id)
        if details:
            # 显示头像
            avatar_path = details[6]
            self.line_3.setText(details[2])
            self.line_4.setText(details[3])
            if avatar_path and path.exists(avatar_path):
                img_path=avatar_path
            else:
                default_avatar = ':/images/resources/icons/person.png'
                img_path=default_avatar
            self.avatar_label.setPixmap(img_path)
            
            # 更新记住API Key选项
            self.remember_check.setChecked(details[4])
            self.auto_login_check.setChecked(details[5])
    
    def login(self):
        """登录选中的账户"""
        current_item = self.account_combo.currentIndex()
        account_id = self.account_combo.itemData(current_item)
        details = self.account_manager.get_account_details(account_id)
        if not details:
            QMessageBox.warning(self, "错误", "获取账户信息失败！")
            return
        
        if not self.remember_check.isChecked():
            self.account_manager.update_account(
                account_id,
                apikey='',
                tavilykey='',
                remember_apikey=False,
                auto_login=False
            )
        else:
            self.account_manager.update_account(
                account_id,
                apikey=self.line_3.text(),
                Tavilykey=self.line_4.text(),
                remember_apikey=True,
                auto_login=self.auto_login_check.isChecked()
            )
        # 通知父窗口登录成功
        self.login_success(details)
    
    def login_success(self,account_details):
        """自动登录"""
        current_account = {
            'modeltype': account_details[0],
            'modelname': account_details[1],
            'apikey': self.line_3.text(),
            'Tavilykey': self.line_4.text(),
        }
        if account_details[7]:
            current_account['api_base']=account_details[7]
        avatar_path=''
        if account_details[6] and path.exists(account_details[6]):
            avatar_path=account_details[6]
        self.login_run.emit(current_account,avatar_path)

    def on_delete_btn_clicked(self):
        """删除选中的账户"""
        current = self.account_combo.currentIndex()
        account_id = self.account_combo.itemData(current)
        self.account_manager.delete_account(account_id)
        self.refresh_accounts()
        self.line_3.clear()
        self.line_4.clear()

    def closeEvent(self, event):
        # 只有直接点击窗口关闭按钮时才退出程序
        if not self.sender():  # 没有信号发射源说明是窗口关闭按钮
            self.request_quit.emit()
        event.accept()

class UserPage(QWidget):
    def __init__(self,accountmanager,parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户信息")
        self.setWindowFlag(Qt.Window)
        self.resize(320, 400)
        self.setFixedWidth(320)
        self.accountmanager=accountmanager
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        label_style="""
            QLabel { 
                color: None; 
                font: 15px "Segoe UI";
                font-weight: bold;
                }"""
        self.label = QLabel(self)
        self.label.setPixmap(QPixmap(self.parent().personavator))
        self.label.setFixedSize(160,160)
        self.label.setScaledContents(True)
        
        self.log_text = QTextEdit()
        show_area=QWidget()
        show_layout = QFormLayout(show_area)
        show_area.setLayout(show_layout)
        
        label_1=QLabel("模型类别:")
        self.label_2=QLabel()
        label_3=QLabel("模型名称:")
        self.label_4=QLabel()
        for i in [label_1,self.label_2,label_3,self.label_4]:
            i.setStyleSheet(label_style)

        show_layout.addRow(label_1,self.label_2)
        show_layout.addRow(label_3,self.label_4)

        btn_area=QWidget()
        btn_layout=QHBoxLayout(btn_area)
        btn_style="""
    QPushButton {
        background-color: #0099ff;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
    }
    QPushButton:hover {
        background-color: #0066cc;
        color:#458fda;                          
    }
"""
        open_button = QPushButton("更换头像")
        open_button.setStyleSheet(btn_style)
        open_button.clicked.connect(lambda:self.open_file_dialog())

        change_button = QPushButton("切换模型")
        change_button.setStyleSheet(btn_style)
        change_button.clicked.connect(self.on_change_button_clicked)
        btn_layout.addWidget(open_button)
        btn_layout.addWidget(change_button)

        main_layout.addWidget(self.label,alignment=Qt.AlignCenter)
        main_layout.addWidget(show_area,alignment=Qt.AlignCenter)
        main_layout.addWidget(btn_area)
        self.update_text()
    def open_file_dialog(self):
        """打开文件对话框并获取路径"""
        # file_dialog = QFileDialog(self)
        file_path, _ = QFileDialog(self).getOpenFileName(
            parent=self,
            caption="选择图片",
            dir="",  # 默认目录（空表示当前目录）
            filter="图片 (*.png *.jpg *.svg *.ico)"
        )
        if file_path:  # 如果用户没有取消选择
            try:
                modeltype=self.parent().current_account['modeltype']
                accountid=self.accountmanager.get_account_id_by_modeltype(modeltype)
                newavatar=self.accountmanager.update_avatar(accountid,file_path)
                self.parent().personavator=self.parent().get_circle_icon(newavatar,300)
                self.label.setPixmap(QPixmap(self.parent().personavator))
                self.parent().btn.setIcon(QIcon(self.parent().personavator))
            except Exception as e:
                QMessageBox.warning(self, "错误", f"头像更新失败：{str(e)}")

    def on_change_button_clicked(self):
        self.close()
        self.parent().show_changeaccount_page()

    def update_text(self):
        self.label_2.setText(f"{self.parent().current_account['modeltype']}")
        self.label_4.setText(f"{self.parent().current_account['modelname']}")

class ChangeAccountPage(QDialog):
    """账户登录页面"""
    def __init__(self, account_manager, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.account_manager = account_manager
        self.setWindowTitle("更换模型")
        self.setModal(True)
        self.setWindowFlags(
            self.windowFlags() |
            Qt.WindowMinimizeButtonHint | # 最小化按钮
            Qt.WindowCloseButtonHint      # 关闭按钮
            |Qt.WindowType.WindowStaysOnTopHint
        )
        
        self.setWindowIcon(QIcon(':/images/resources/icons/ouricon.png'))
        self.resize(320, 400)
        self.setFixedWidth(320)
        
        layout = QVBoxLayout(self)
        
        # 头像预览
        self.avatar_label = CircleImageLabel(size=100)
        
        #勾选区域
        check_area=QWidget()
        cheack_layout=QHBoxLayout(check_area)
        
        # 记住API Key
        self.remember_check = QCheckBox("记住API Key")
        
        # 自动登录
        self.auto_login_check = QCheckBox("自动登录")
        cheack_layout.addWidget(self.remember_check)
        cheack_layout.addWidget(self.auto_login_check)


        # 账户列表
        self.set_area()
        self.account_combo.currentIndexChanged.connect(self.update_account_preview)
        self.refresh_accounts()

        # 按钮
        btn_style="""
            QPushButton {
                background-color: #0099ff;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #0066cc;
                color:#458fda;                          
            }
"""
        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("选择")
        self.login_btn.setStyleSheet(btn_style)
        self.login_btn.clicked.connect(self.login)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color:#ff6d1f ;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #FF5765;
                color:white;                          
            }
                """)
        self.delete_btn.clicked.connect(self.on_delete_btn_clicked)

        btn_layout.addWidget(self.delete_btn,1)
        btn_layout.addWidget(self.login_btn,3)

        self.register_btn = QPushButton("新账户")
        self.register_btn.setStyleSheet(btn_style)
        self.register_btn.clicked.connect(self.open_register)
        
        layout.addWidget(self.avatar_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.set_area)
        layout.addWidget(check_area)
        layout.addWidget(self.register_btn)
        layout.addLayout(btn_layout)

    def set_area(self):
        self.set_area = QWidget()
        self.layout = QFormLayout(self.set_area)
        label_1=QLabel("模型:")
        self.account_combo=QComboBox(self)
        self.account_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        label_style="""
            QLabel { 
                color: None; 
                font: 15px "Segoe UI";
                font-weight: bold;
                }"""

        label_1.setStyleSheet(label_style)
        combo_style=f"""
            QComboBox {{
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 1px 2px 1px 2px;
                min-width: 6em;
                font: 15px "Segoe UI";
            }}
            QComboBox:hover {{
                border: 1px solid #0099ff;
            }}
            /*QCombobox右侧按钮*/
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;/*放于右方顶部*/
                width: 30px;/*设置按钮范围宽度*/
                border-top-right-radius: 3px;/*设置边框圆角*/
                border-bottom-right-radius: 3px;
                /*padding-right: 50px;*/
            }}
            QComboBox::down-arrow {{
                image: url(:/images/resources/icons/drop.svg);
                width: 24px;/*设置该图标的宽高*/
                height: 24px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #0099ff;
                border-radius: 10px;
                outline:0px;
                padding: 2px;}}
            QComboBox QAbstractItemView::item {{
                
                font: 15px "Segoe UI";
                height: 36px;   /* 项的高度（设置pComboBox->setView(new QListView());后，该项才起作用） */
                border:none;
                background-color: none;
            }}
            QComboBox QAbstractItemView::item:last-child {{
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                border-bottom: none;
            }}
            QComboBox QAbstractItemView::item:hover {{
                color: white;
                /* 整个下拉窗体越过每项的背景色 */
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            /* 下拉后，整个下拉窗体被选择的每项的样式 */
            QComboBox QAbstractItemView::item:selected {{
                color: white;
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            """
        self.account_combo.setStyleSheet(combo_style)

        label_3=QLabel("Apikey:")
        self.line_3=QLineEdit(self)
        self.line_3.setPlaceholderText("请输入您对应模型的apikey")
        self.line_3.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_3.setClearButtonEnabled(True)
        self.line_3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label_4=QLabel("Tavilykey:")
        self.line_4=QLineEdit(self)
        self.line_4.setPlaceholderText("搜索引擎工具key,没有留空即可")
        self.line_4.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_4.setClearButtonEnabled(True)
        self.line_4.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        label_3.setStyleSheet(label_style)
        label_4.setStyleSheet(label_style)
        line_style="""
            QLineEdit {
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QLineEdit:hover {
                background-color: #0099ff;
                color:white;                          
            }
            QLineEdit:focus {
                background-color: #0099ff;
            }
                """
        self.line_3.setStyleSheet(line_style)
        self.line_4.setStyleSheet(line_style)
        
        self.layout.addRow(label_1, self.account_combo)
        self.layout.addRow(label_3, self.line_3)
        self.layout.addRow(label_4, self.line_4)
        self.set_area.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
    
    def refresh_accounts(self):
        """刷新账户列表"""
        self.account_combo.clear()
        accounts = self.account_manager.get_accounts()
        for acc in accounts:
            item = f"{acc[1]} - {acc[2]}"
            self.account_combo.addItem(item,userData=acc[0])
   
        if self.account_combo.count() > 0:
            # 初始化时建立映射
            self.userdata_to_index = {
                self.account_combo.itemData(i): i 
                for i in range(self.account_combo.count())
            }
            # 查询时直接使用字典
            index = self.userdata_to_index.get(self.parent().current_accountid, 0) 
            self.account_combo.setCurrentIndex(index)

    def update_account_preview(self, current):
        """更新账户预览信息"""
        account_id = self.account_combo.itemData(current)
        details = self.account_manager.get_account_details(account_id)
        if details:
            # 显示头像
            avatar_path = details[6]
            self.line_3.setText(details[2])
            self.line_4.setText(details[3])
            if avatar_path and path.exists(avatar_path):
                img_path=avatar_path
            else:
                default_avatar = ':/images/resources/icons/person.png'
                img_path=default_avatar
            self.avatar_label.setPixmap(img_path)
            
            # 更新记住API Key选项
            self.remember_check.setChecked(details[4])
            self.auto_login_check.setChecked(details[5])
    
    def login(self):
        """登录选中的账户"""
        current_item = self.account_combo.currentIndex()
        account_id = self.account_combo.itemData(current_item)
        details = self.account_manager.get_account_details(account_id)
        if not details:
            QMessageBox.warning(self, "错误", "获取账户信息失败！")
            return
        
        if not self.remember_check.isChecked():
            self.account_manager.update_account(
                account_id,
                apikey='',
                tavilykey='',
                remember_apikey=False,
                auto_login=False
            )
        else:
            self.account_manager.update_account(
                account_id,
                apikey=self.line_3.text(),
                Tavilykey=self.line_4.text(),
                remember_apikey=True,
                auto_login=self.auto_login_check.isChecked()
            )
        # 通知父窗口登录成功
        self.parent().login_success(details)
        self.accept()
    
    def open_register(self):
        """打开注册页面"""
        self.reject()
        self.parent().show_addaccount_page()            

    def on_delete_btn_clicked(self):
        """删除选中的账户"""
        current = self.account_combo.currentIndex()
        account_id = self.account_combo.itemData(current)
        self.account_manager.delete_account(account_id)
        self.refresh_accounts()
        self.line_3.clear()
        self.line_4.clear()

class AddAccountPage(QDialog):
    def __init__(self,account_manager,parent=None):
        super().__init__(parent)
        self.setWindowTitle("注册")
        self.setModal(True)
        self.resize(360, 430)
        self.setFixedWidth(360)
        self.setMaximumHeight(560)
        self.setContentsMargins(15,15,5,15)
        self.setWindowIcon(QIcon(':/images/resources/icons/ouricon.svg'))
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint|Qt.WindowType.WindowStaysOnTopHint|self.windowFlags() | Qt.WindowType.Window)
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # self.setStyleSheet("""
        #     QDialog {
        #         border-radius: 10px;
        #         background: none;
        #     }
        # """)
        self.success=None
        self.account_manager=account_manager
        
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        label=QLabel(self)
        label.setPixmap(QPixmap(':/images/resources/icons/ouricon.svg'))
        label.setFixedSize(230,120)
        label.setScaledContents(True)

        self.set_area()

        #勾选区域
        check_area=QWidget()
        cheack_layout=QHBoxLayout(check_area)
        # 记住API Key
        self.remember_check = QCheckBox("记住API Key")
        # 自动登录
        self.auto_login_check = QCheckBox("自动登录")
        cheack_layout.addWidget(self.remember_check)
        cheack_layout.addWidget(self.auto_login_check)

        # 运行按钮
        run_button=QPushButton("开始使用",self)
        back_button=QPushButton("返回",self)
        btn_style="""
    QPushButton {
        background-color: #0099ff;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
    }
    QPushButton:hover {
        background-color: #0066cc;
        color:#458fda;                          
    }
"""
        run_button.setStyleSheet(btn_style)
        back_button.setStyleSheet(btn_style)
        btn_area=QWidget()
        btn_layout=QHBoxLayout(btn_area)
        btn_layout.addWidget(back_button,1)
        btn_layout.addWidget(run_button,3)

        main_layout.setSpacing(15)
        main_layout.addWidget(label,0,alignment=Qt.AlignCenter)
        main_layout.addWidget(self.set_area,1)
        main_layout.addWidget(check_area)
        main_layout.addWidget(btn_area)

        run_button.clicked.connect(lambda:self.on_run_button_clicked())
        back_button.clicked.connect(lambda:self.on_back_button_clicked())
        self._setup_threading()

    def set_area(self):
        self.set_area = QWidget(self)
        self.layout = QFormLayout(self.set_area)
        label_1=QLabel("模型类别:")
        self.combo_1=QComboBox(self)
        self.combo_1.setEditable(True)
        self.combo_1.addItems(['deepseek','qwen','siliconflow'])
        self.combo_1.setCurrentIndex(-1)
        self.combo_1.currentIndexChanged.connect(self.on_combo_1_changed)
        self.combo_1.lineEdit().editingFinished.connect(self.on_combo_1_edited)
        self.combo_1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label_2=QLabel("模型名称:")
        self.combo_2=QComboBox(self)
        self.combo_2.addItem('请先选择模型类别!')
        self.combo_2.setEditable(True)
        self.combo_2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label_style="""
            QLabel { 
                color: None; 
                font: 15px "Segoe UI";
                font-weight: bold;
                }"""

        label_1.setStyleSheet(label_style)
        label_2.setStyleSheet(label_style)
        combo_style=f"""
            QComboBox {{
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 1px 2px 1px 2px;
                min-width: 6em;
                font: 15px "Segoe UI";
            }}
            QComboBox:hover {{
                border: 1px solid #0099ff;
            }}
            /*QCombobox右侧按钮*/
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;/*放于右方顶部*/
                width: 30px;/*设置按钮范围宽度*/
                border-top-right-radius: 3px;/*设置边框圆角*/
                border-bottom-right-radius: 3px;
                /*padding-right: 50px;*/
            }}
            QComboBox::down-arrow {{
                image: url(:/images/resources/icons/drop.svg);
                width: 24px;/*设置该图标的宽高*/
                height: 24px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #0099ff;
                border-radius: 10px;
                outline:0px;
                padding: 2px;}}
            QComboBox QAbstractItemView::item {{
                
                font: 15px "Segoe UI";
                height: 36px;   /* 项的高度（设置pComboBox->setView(new QListView());后，该项才起作用） */
                border:none;
                background-color: none;
            }}
            QComboBox QAbstractItemView::item:last-child {{
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                border-bottom: none;
            }}
            QComboBox QAbstractItemView::item:hover {{
                color: white;
                /* 整个下拉窗体越过每项的背景色 */
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            /* 下拉后，整个下拉窗体被选择的每项的样式 */
            QComboBox QAbstractItemView::item:selected {{
                color: white;
                border-radius: 10px;/*圆角*/
                background-color: #0099ff;
                outline: none;
            }}
            """
        self.combo_1.setStyleSheet(combo_style)
        self.combo_2.setStyleSheet(combo_style)

        label_3=QLabel("Apikey:")
        self.line_3=QLineEdit(self)
        self.line_3.setPlaceholderText("请输入您对应模型的apikey")
        self.line_3.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_3.setClearButtonEnabled(True)
        self.line_3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label_4=QLabel("Tavilykey:")
        self.line_4=QLineEdit(self)
        self.line_4.setPlaceholderText("搜索引擎工具key,没有留空即可")
        self.line_4.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.line_4.setClearButtonEnabled(True)
        self.line_4.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        label_3.setStyleSheet(label_style)
        label_4.setStyleSheet(label_style)
        line_style="""
            QLineEdit {
                background-color: None;
                color: None;
                border: 1px solid #0099ff;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QLineEdit:hover {
                background-color: #0099ff;
                color:white;                          
            }
            QLineEdit:focus {
                background-color: #0099ff;
                color:white;
            }
                """
        self.line_3.setStyleSheet(line_style)
        self.line_4.setStyleSheet(line_style)
        
        self.label_5=QLabel("Api_Base:")
        self.line_5=QLineEdit()
        self.line_5.setPlaceholderText("请输入自定义模型的baseurl")
        self.label_5.setStyleSheet(label_style)
        self.line_5.setStyleSheet(line_style)
        self.line_5.setClearButtonEnabled(True)
        self.line_5.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.layout.addRow(label_1, self.combo_1)
        self.layout.addRow(label_2, self.combo_2)
        self.layout.addRow(label_3, self.line_3)
        self.layout.addRow(label_4, self.line_4)
        self.set_area.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)

    @Slot(int)
    def on_combo_1_changed(self, index):
        if index == 0:
            self.combo_2.clear()
            self.combo_2.addItems(['deepseek-chat','deepseek-reasoner'])
        elif index == 1:
            self.combo_2.clear()
            self.combo_2.addItems(["qwen-turbo", "qwq-plus","qwen-plus"])
        elif index == 2:
            self.combo_2.clear()
            self.combo_2.addItems(["Qwen/Qwen2.5-72B-Instruct-128K", "Qwen/QwQ-32B"])
        if self.layout.rowCount()==5:
            item=self.layout.takeRow(3)
            self.label_5.hide()
            self.line_5.hide()
    
    def on_run_button_clicked(self):
        modeltype=self.combo_1.currentText()
        modelname=self.combo_2.currentText()
        apikey=self.line_3.text()
        tavilykey=self.line_4.text()
        api_base=self.line_5.text()
        if not all([modeltype,modelname,apikey]):
            QMessageBox.warning(self, "警告", "请填写完整信息！")
            return
        keywards={'modeltype':modeltype,'modelname':modelname,'apikey':apikey,'Tavilykey':tavilykey}
        if api_base:
            keywards['api_base']=api_base
        try:
            if self.remember_check.isChecked():
                self.success = self.account_manager.add_account(
                    modeltype=modeltype,
                    modelname=modelname,
                    apikey=apikey,
                    tavilykey=tavilykey,
                    remember_apikey=self.remember_check.isChecked(),
                    auto_login=self.auto_login_check.isChecked(),
                    avatar_path=':images/resources/icons/person.png',
                    api_base=api_base
                )
            else:
                self.success = self.account_manager.add_account(
                    modeltype=modeltype,
                    modelname=modelname,
                    apikey=None,
                    tavilykey=None,
                    remember_apikey=self.remember_check.isChecked(),
                    auto_login=self.auto_login_check.isChecked(),
                    avatar_path=':images/resources/icons/person.png',
                    api_base=api_base
                )
        except Exception as e:
            QMessageBox.warning(self, "警告", f"[ERROR]{e}")
        if not self.success:
            result=QMessageBox.critical(self, "警告", "该模型账户已存在！是否选择覆盖原账号",QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Ok)
            if result==QMessageBox.StandardButton.Ok:
                self.account_manager.update_account_pro(**keywards)
        self.parent().init_agent(keywards)
        self.accept()
    
    def on_back_button_clicked(self):
        self.reject()
        self.parent().show_changeaccount_page()

    def on_update_finished(self):
        if self.success:
            self.close()
    
    def _setup_threading(self):
        self.parent().ai_worker.update_finished.connect(self.on_update_finished)

    def on_combo_1_edited(self):
        text=self.combo_1.currentText()
        if text not in [self.combo_1.itemText(i) for i in range(self.combo_1.count())] and text:
            self.combo_2.clear()
            self.combo_2.setPlaceholderText("输入自定义模型名称")
            self.label_5.show()
            self.line_5.show()
            self.layout.insertRow(3,self.label_5, self.line_5)

class MainWindow(QMainWindow):
    update_agent=Signal(object,dict)

    def __init__(self,current_account:dict,avatar_path:str,account_manager):
        super().__init__()
        self.setWindowTitle("NewVC")
        self.setWindowIcon(QIcon(':/images/resources/icons/ouricon.png'))
        self.resize(800, 700)
        # 设置中心窗口
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setLayout(self.show_loading())
        QThread.currentThread().setPriority(QThread.TimeCriticalPriority)
        self._setup_threading()
        self.agent=Newvc(init_after=True)
        self.FirstTime=True
        self.update_agent.emit(self.agent,current_account)
        #self.setWindowFlags(Qt.CustomizeWindowHint)
        #self.setWindowFlags(Qt.FramelessWindowHint)
        # self.agent=Newvc(apikey=siliconapikey,modeltype='siliconflow',modelname=siliconmodel,Tavilykey=Tavilykey,TYPE='verilog',maxitems=20)
        self.current_accountid=None
        self.changeaccountpage=None
        self.addaccountpage=None
        self.account_manager = account_manager        
        self.avator_path=avatar_path
        self.current_account = current_account
                
    def show_loading(self):
        loading_label = QLabel(self)
        movie=QMovie(':/images/resources/icons/loading2.gif')
        movie.start()
        # movie.setScaledSize(QSize(240, 240))
        movie.start()
        loading_label.setMovie(movie)
        temp_layout=QVBoxLayout()
        temp_layout.addWidget(loading_label,alignment=Qt.AlignCenter)
        return temp_layout

    def init_ui(self):
        # 主布局
        if  not self.current_accountid:
            self.current_accountid=self.account_manager.get_account_id_by_modeltype(self.current_account['modeltype'])
        if not self.avator_path:
            self.avator_path=':/images/resources/icons/person.png'
            self.account_manager.update_avatar(self.current_accountid,self.avator_path)
        self.FirstTime=False
        # 左侧导航栏
        self.nav_bar = NavWidget()

        self.nav_bar.setAttribute(Qt.WA_StyledBackground, True)
        
        self.personavator=self.get_circle_icon(self.avator_path,300)
        self.btn=QPushButton(QIcon(self.personavator),'')
        self.btn_1 = AnimatedNavButton(':images/resources/icons/chat.svg', "聊天")
        self.btn_2 = AnimatedNavButton(':images/resources/icons/log.svg', "日志")
        self.btn_3 = AnimatedNavButton(":images/resources/icons/set.svg", "设置")
        self.btn_4 = AnimatedNavButton(':images/resources/icons/about.svg', "关于")
        
        style_2 = """
        QPushButton {
            border: none;
            border-radius: 50%;
            min-width: 24px;
            min-height: 24px;          
        }
            """
        self.btn.setStyleSheet(style_2)
        
        # 连接信号
        self.btn_1.clicked.connect(lambda: self.switch_page(0))
        self.btn_2.clicked.connect(lambda: self.switch_page(1))
        self.btn_3.clicked.connect(lambda: self.switch_page(2))
        self.btn_4.clicked.connect(lambda: self.switch_page(3))

        # 添加到导航布局
        self.nav_bar.addAvator(self.btn)
        self.nav_bar.addButton(self.btn_1)
        self.nav_bar.addButton(self.btn_2)
        self.nav_bar.layout.addStretch()
        self.nav_bar.addButton(self.btn_3)
        self.nav_bar.addButton(self.btn_4)
        
        #根据系统深浅色变化确定控件样式
        # 设置按钮样式
        style_1 = """
        QPushButton {
            border: none;
            padding: 15px;
            /*text-align: left;*/
            spacing: 100px;
            font-size: 15px;
            border-radius: 10px;
            color:white            
        }
        QPushButton:hover {
            background-color: #33adff;
            color: white;
            font-weight: bold;
            font-size: 18px;
        }
        QPushButton:pressed {
            background-color: #33adff;
            spacing: 100px;
            color: #33adff;
            font-weight: bold;
            font-size: 18px;
        }
        QPushButton:checked {
            background-color: #33adff;
            color: white;
            font-weight: bold;
            font-size: 18px;
        }
        """
        style_dark="""
        QPushButton {
            border: none;
            padding: 15px;
            /*text-align: left;*/
            spacing: 100px;
            font-size: 15px;
            border-radius: 10px;
            color:white            
        }
        QPushButton:hover {
            background-color: #4A4A4B;
            color: white;
            font-weight: bold;
            font-size: 18px;
        }
        QPushButton:pressed {
            background-color: #4A4A4B;
            spacing: 100px;
            color: #4A4A4B;
            font-weight: bold;
            font-size: 18px;
        }
        QPushButton:checked {
            background-color: #4A4A4B;
            color: white;
            font-weight: bold;
            font-size: 18px;
        }
        """
        
        if self.is_system_dark_theme():
            self.nav_bar.setStyleSheet("background-color: #1D1D1E;")
            self.btn_1.setStyleSheet(style_dark)
            self.btn_2.setStyleSheet(style_dark)
            self.btn_3.setStyleSheet(style_dark)
            self.btn_4.setStyleSheet(style_dark)
        else:
            self.nav_bar.setStyleSheet("background-color: #0099ff;")
            self.btn_1.setStyleSheet(style_1)
            self.btn_2.setStyleSheet(style_1)
            self.btn_3.setStyleSheet(style_1)
            self.btn_4.setStyleSheet(style_1)



        # 右侧内容区
        self.content_area = QStackedWidget()

        chatpage=ChatPage(self.agent,self)
        logpage=LogPage(self)
        self.settingspage=SettingsPage(self.account_manager,self.agent,self.current_account,parent=self)
        aboutpage=AboutPage(self)
        self.userpage=UserPage(self.account_manager,parent=self)
        self.content_area.addWidget(chatpage)
        self.content_area.addWidget(logpage)
        self.content_area.addWidget(self.settingspage)
        self.content_area.addWidget(aboutpage)
        
        central_widget = QWidget()
        # 添加到主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.nav_bar)
        main_layout.addWidget(self.content_area)

        central_widget.setLayout(main_layout)
        old_widget = self.centralWidget() 
        self.setCentralWidget(central_widget)
        self.switch_page(-1)

        self.btn.clicked.connect(lambda: self.userpage.show())
        if old_widget:
            old_widget.deleteLater()

    def get_circle_icon(self,image_path: str, size: int) -> QIcon:
        pixmap = QPixmap(image_path).scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        result = QPixmap(size, size)
        result.fill(Qt.transparent)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        path.addEllipse(0, 0, size, size)

        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return result
    
    def switch_page(self, index):
        """切换页面"""
        self.content_area.setCurrentIndex(index)

    def closeEvent(self, event):
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
        if not self.worker_thread.wait(3000): # Wait up to 3 seconds
            self.worker_thread.terminate()
            self.worker_thread.wait()
        super().closeEvent(event)
        
    def show_changeaccount_page(self):
        """显示登录对话框"""
        self.changeaccountpage = ChangeAccountPage(self.account_manager, parent=self)
        self.changeaccountpage.exec()
        
    def show_addaccount_page(self):
        """显示注册对话框"""
        self.addaccountpage = AddAccountPage(self.account_manager, parent=self)
        self.addaccountpage.exec()
    
    def login_success(self, account_details):
        """登录成功处理"""
        self.current_account.update({
            'modeltype': account_details[0],
            'modelname': account_details[1],
            'apikey': account_details[2],
            'Tavilykey': account_details[3],
        })
        self.current_accountid=self.account_manager.get_account_id_by_modeltype(self.current_account['modeltype'])
        # 初始化agent
        self.update_agent.emit(self.agent,self.current_account)
        if account_details[6] and (path.exists(account_details[6]) or QFile.exists(account_details[6])):
            self.avator_path=account_details[6]

    def init_agent(self,kwargs:dict):
        self.current_account.update(kwargs)
        self.current_accountid=self.account_manager.get_account_id_by_modeltype(self.current_account['modeltype'])
        self.update_agent.emit(self.agent,self.current_account)

    def _setup_threading(self):
        """设置线程"""
        self.worker_thread = QThread(self)
        self.ai_worker = AIWorker()
        self.ai_worker.moveToThread(self.worker_thread)
        # 确保请求通过队列处理
        self.worker_thread.start()
        self.update_agent.connect(self.ai_worker.update_agent)
        self.ai_worker.update_finished.connect(self.on_update_finished)
        self.ai_worker.err_occured.connect(self.on_err_occured)


    def on_update_finished(self):
        if self.FirstTime:
            self.init_ui()
        else:
            self.settingspage.update_text()
            self.userpage.update_text()
            self.changeaccountpage.refresh_accounts()
            #更新头像
            newavatar=self.avator_path
            self.personavator=self.get_circle_icon(newavatar,300)
            self.userpage.label.setPixmap(QPixmap(self.personavator))
            self.btn.setIcon(QIcon(self.personavator))
            
    def on_err_occured(self,text):
        QMessageBox.critical(self, "AIWorker错误",text,QMessageBox.StandardButton.Ok)

    def is_system_dark_theme(self):
        """检测系统是否处于深色模式（跨平台方法）"""
        settings = QSettings("HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", QSettings.NativeFormat)
        return settings.value("AppsUseLightTheme", 1, int) == 0

class NewVCAPP():
    def __init__(self):
        self.app = QApplication(sys.argv)
        QCoreApplication.setApplicationName("NewVC")
        QCoreApplication.setOrganizationName("SEU-2025")
        QCoreApplication.setApplicationVersion("1.0.3")

        self.app.setStyle(QStyleFactory.create("Fusion"))
        self.account_manager=AccountManager()
        self.firstpage=None
        self.registerpage=None
        self.check_auto_login()
        self.app.exec()

    def on_login_success(self,account_details,avatar_path):
        if self.firstpage:
            self.firstpage.close()
        if self.registerpage:
            self.registerpage.close()
        self.window = MainWindow(account_details,avatar_path,self.account_manager)
        self.window.show()
        
    def on_open_login(self):
        self.firstpage=FirstPage(self.account_manager)
        self.firstpage.login_run.connect(self.on_login_success)
        self.firstpage.open_register_run.connect(self.on_open_register)
        self.firstpage.request_quit.connect(self.app.quit)
        self.firstpage.show()

    def on_open_register(self,showmessage:bool=False):
        if self.firstpage:
            self.firstpage.close()
        self.registerpage=RegisterPage(self.account_manager,showmessage=showmessage)
        self.registerpage.show()
        self.registerpage.run.connect(lambda kwargs:self.on_login_success(kwargs,''))
        
    def check_auto_login(self):
        """检查自动登录"""
        auto_login_id = self.account_manager.get_auto_login_account()
        accounts = self.account_manager.get_accounts()
        if auto_login_id:
            details = self.account_manager.get_account_details(auto_login_id)
            if details:
                self.login_success(details)
        elif accounts:
            self.on_open_login()
        else:
            self.on_open_register(showmessage=True)
    
    def login_success(self,account_details):
        """自动登录"""
        current_account = {
            'modeltype': account_details[0],
            'modelname': account_details[1],
            'apikey': account_details[2],
            'Tavilykey': account_details[3],
        }
        avatar_path=''
        if account_details[6] and path.exists(account_details[6]):
            avatar_path=account_details[6]
        self.on_login_success(current_account,avatar_path)

if __name__ == "__main__":
    a=NewVCAPP()