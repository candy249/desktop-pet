import random
import time

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QTransform
from PyQt5.QtWidgets import QMenu, QApplication, QSystemTrayIcon, QAction, QMainWindow
import win32gui
import win32con
import win32api

from core import action
from core.ability import Ability
from core.conf import settings


class DesktopPet(QMainWindow):
    def __init__(self, parent=None, tray=False):
        super(DesktopPet, self).__init__(parent)
        # 图片资源根目录
        self.imgDir = settings.SETUP_DIR / "img"
        self.walking = False          # 是否处于自动行走状态
        self.playing = False          # 是否正在播放随机待机动作动画
        self.draging = False          # 是否正在被鼠标拖拽
        self.autoFalling = False      # 自由落体功能开关
        self.contenting = False       # 右键菜单弹窗锁标记
        self.mDragPosition = None     # 拖拽起始坐标缓存
        self._is_drag_action = False  # 区分本次左键是单击还是拖拽
        self.tray_mode = tray         # 是否使用托盘后台模式启动

        # 置顶相关设置
        self.is_topmost = True
        self.user_enable_top = True
        # 定时检测全屏程序，打开全屏游戏/视频时自动取消置顶
        self.check_fullscreen_timer = QTimer()
        self.check_fullscreen_timer.timeout.connect(self.detect_fullscreen_app)
        self.check_fullscreen_timer.start(500)
        self.walk_left = True         # 默认初始行走方向：向左
        self.walk_paused = False      # 行走临时暂停标记（拖拽使用）

        # 行走动画参数
        self.walk_frame_index = 0
        self.walk_timer = QTimer()
        self.walk_timer.timeout.connect(self.walk_frame_update)
        self.walk_interval = 500

        # 系统托盘对象
        self.tray_icon = None
        self.action_show = None

        self.initUI()

        # 如果是托盘模式，先初始化托盘，再隐藏主窗口
        if self.tray_mode:
            self.init_tray()
            self.hide()

        # 启动随机待机动画定时器
        self.startMovie()

    def initUI(self):
        """基础窗口UI初始化：无边框、透明背景、窗口图标"""
        self.setWindowIcon(QIcon(str(self.imgDir / settings.ICON)))
        self.desktop = QApplication.desktop()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

    def init_tray(self):
        """托盘初始化"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(str(self.imgDir / settings.TRAY_ICON)))
        self.tray_icon.setToolTip("桌面宠物")

        tray_menu = QMenu()
        self.action_show = QAction("", self)
        self.action_show.triggered.connect(self.toggle_window)
        action_quit = QAction("退出程序", self)
        action_quit.triggered.connect(self.close)

        tray_menu.addAction(self.action_show)
        tray_menu.addAction(action_quit)
        self.tray_icon.setContextMenu(tray_menu)

        # 初始化时自动同步托盘文字
        self.refresh_tray_text()

        self.tray_icon.activated.connect(self.on_tray_click)
        self.tray_icon.show()

    def refresh_tray_text(self):
        """
        根据窗口实时可见状态，自动刷新托盘菜单文字
        self.isVisible()：Qt原生自带变量，自动识别窗口显示/隐藏
        窗口显示 → 文字：隐藏宠物
        窗口隐藏 → 文字：显示宠物
        """
        if self.isVisible():
            self.action_show.setText("隐藏宠物")
        else:
            self.action_show.setText("显示宠物")

    def on_tray_click(self, reason):
        """单击托盘图标响应"""
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_window()

    def toggle_window(self):
        """切换宠物窗口显示/隐藏"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
        # 切换窗口状态后，立刻更新托盘文字
        self.refresh_tray_text()

    def refresh_top_flag(self):
        """刷新窗口置顶状态"""
        flags = self.windowFlags()
        flags &= ~Qt.WindowStaysOnTopHint
        if self.is_topmost:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    def toggle_topmost(self):
        """右键菜单：切换置顶开关"""
        self.user_enable_top = not self.user_enable_top
        self.is_topmost = self.user_enable_top
        self.refresh_top_flag()

    def detect_fullscreen_app(self):
        """定时检测前台全屏程序，全屏时自动取消置顶，避免遮挡游戏"""
        if not self.user_enable_top:
            return
        hwnd = win32gui.GetForegroundWindow()
        if hwnd == 0:
            return
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

        is_full = (right - left >= screen_w) and (bottom - top >= screen_h)
        if is_full and self.is_topmost:
            self.is_topmost = False
            self.refresh_top_flag()
        elif not is_full and not self.is_topmost:
            self.is_topmost = True
            self.refresh_top_flag()

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if self.playing:
            return
        if event.button() == Qt.LeftButton:
            self.mDragPosition = event.globalPos() - self.pos()
            # 初始状态：还没判定为拖拽
            self._is_drag_action = False
            event.accept()

    def mouseMoveEvent(self, event):
        """拖拽过程切换拖动贴图"""
        if self.playing:
            return
        # 必须判断 mDragPosition 不为空，避免None运算报错
        if event.buttons() & Qt.LeftButton and self.mDragPosition is not None:
            # 只要发生移动，就标记为拖拽操作
            self._is_drag_action = True
            self.move(event.globalPos() - self.mDragPosition)

            moveDistance = (self.mDragPosition - event.pos()).x()

            if -1 <= moveDistance < 0:
                self.setPix(str(self.imgDir / settings.MOUSE_TO_RIGHT_1))
            elif -2 <= moveDistance < -1:
                self.setPix(str(self.imgDir / settings.MOUSE_TO_RIGHT_2))
            elif moveDistance < -2:
                self.setPix(str(self.imgDir / settings.MOUSE_TO_RIGHT_3))
            elif 0 < moveDistance <= 1:
                self.setPix(str(self.imgDir / settings.MOUSE_TO_LEFT_1))
            elif 1 < moveDistance <= 2:
                self.setPix(str(self.imgDir / settings.MOUSE_TO_LEFT_2))
            elif 2 < moveDistance:
                self.setPix(str(self.imgDir / settings.MOUSE_TO_LEFT_3))

    def mouseReleaseEvent(self, event):
        """鼠标松开：区分【单纯单击】和【拖拽】"""
        if self.mDragPosition is None:
            return

        drag_threshold = 8
        move_offset = event.globalPos() - self.mDragPosition

        # ----------------【修复1】强制逻辑优化 ----------------
        if abs(move_offset.x()) >= drag_threshold or abs(move_offset.y()) >= drag_threshold:
            self.draging = True
        else:
            self.draging = False

        # 行走状态，单纯单击停止行走
        if not self._is_drag_action and self.walking:
            self.stop_walk()

        # ----------------【修复2：拖拽松开，待机状态恢复默认贴图】 ----------------
        if self._is_drag_action and not self.walking:
            self.setPix(str(self.imgDir / settings.INIT_PICTURE))

        # ----------------【修复3：无论如何松开，最后强制清空拖拽标记，根治右键锁死】 ----------------
        self.mDragPosition = None
        self._is_drag_action = False
        self.draging = False

    def mouseDoubleClickEvent(self, QMouseEvent):
        """鼠标双击左键：启动自动行走"""
        if self.playing:
            return
        if Qt.LeftButton == QMouseEvent.button():
            self.start_walk()

    def closeEvent(self, QCloseEvent):
        """程序关闭，资源清理"""
        self.stop_walk()
        if self.tray_icon is not None:
            self.tray_icon.hide()

    def contextMenuEvent(self, e):
        """鼠标右键弹出功能菜单"""
        # 行走/播放动画时禁止弹出右键菜单；拖拽标记已经在release强制清零
        if self.walking or self.playing:
            return

        self.contenting = True
        menu = QMenu(self)
        ability = Ability(self)

        wechat = menu.addAction("打开微信")
        wechat.triggered.connect(ability.openWechat)

        top_action = menu.addAction("切换始终置顶")
        top_action.triggered.connect(self.toggle_topmost)

        fall = menu.addAction("关闭自由落体" if self.autoFalling else "开启自由落体")
        fall.triggered.connect(ability.fall)
        fall.setIcon(QIcon(str(self.imgDir / settings.FALL)))

        close = menu.addAction("退出")
        close.triggered.connect(self.close)
        close.setIcon(QIcon(str(self.imgDir / settings.EXIT)))

        menu.exec_(e.globalPos())
        self.contenting = False

    def paintEvent(self, QPaintEvent):
        """绘制当前图片到透明窗口"""
        painter = QPainter(self)
        if hasattr(self, "pix"):
            painter.drawPixmap(self.rect(), self.pix)

    def setPix(self, pix):
        """切换显示图片，自动适配窗口大小"""
        if isinstance(pix, QPixmap):
            self.pix = pix
        else:
            self.pix = QPixmap(pix)
        self.resize(self.pix.size())
        self.setMask(self.pix.mask())
        self.update()

    def startMovie(self):
        """启动随机待机动画定时器"""
        self.allActions = Action().getAllAction()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.action)
        self.timer.start(settings.MOVIE_TIME_INTERVAL * 1000)

    def action(self):
        """循环播放随机待机动作"""
        if self.draging or self.walking or self.contenting:
            return
        self.timer.stop()
        self.playing = True
        currentMovie = random.choice(self.allActions)
        for i in range(len(currentMovie)):
            pix = currentMovie[i]
            self.setPix(pix)
            QApplication.processEvents()
            time.sleep(0.5)
        self.timer.start()
        self.playing = False
        self.setPix(str(self.imgDir / settings.INIT_PICTURE))

    def welcomePage(self):
        """初始自由落体位置"""
        self.fallingBody(self.desktop.availableGeometry().bottomRight().x() - 300, 0)

    def start_walk(self):
        """开启自动行走"""
        self.walk_left = True
        self.walking = True
        self.walk_paused = False
        self.walk_frame_index = 0
        self.walk_timer.start(self.walk_interval)

    def stop_walk(self):
        """停止自动行走，切换回默认待机图片"""
        self.walking = False
        self.walk_paused = False
        self.walk_timer.stop()
        self.setPix(str(self.imgDir / settings.INIT_PICTURE))

    def walk_frame_update(self):
        """行走每一帧更新逻辑：移动+贴图翻转+边界检测"""
        if not self.walking or self.walk_paused:
            return

        walk_imgs = settings.WALK
        flip_transform = QTransform().scale(-1, 1)
        screen_rect = self.desktop.availableGeometry()
        pet_width = self.width()

        if self.walk_left:
            self.move(self.pos().x() - 5, self.pos().y())
        else:
            self.move(self.pos().x() + 5, self.pos().y())

        pet_x = self.pos().x()
        margin = 1  # 边界距离，数值越小越贴近屏幕边缘换向
        if pet_x <= screen_rect.left() + margin:
            self.walk_left = False
        if pet_x >= screen_rect.right() - pet_width - margin:
            self.walk_left = True

        pix_path = str(self.imgDir / walk_imgs[self.walk_frame_index])
        pix = QPixmap(pix_path)
        if not self.walk_left:
            pix = pix.transformed(flip_transform)
        self.setPix(pix)

        self.walk_frame_index += 1
        if self.walk_frame_index >= len(walk_imgs):
            self.walk_frame_index = 0

    def fallingBody(self, posX, posY):
        """自由落体重力动画"""
        rect = self.desktop.availableGeometry()
        while self.pos().y() < rect.height() - 200:
            self.move(posX, posY)
            self.setPix(str(self.imgDir / "shime4.png"))
            QApplication.processEvents()
            time.sleep(0.01)
            posY += 10
        self.setPix(str(self.imgDir / settings.INIT_PICTURE))


class Action(object):
    """加载action.py内全部待机动画序列"""
    def __init__(self):
        self.imgDir = settings.SETUP_DIR / "img"
        self.actionList = []
        self.picturesList = []

    def createPicture(self):
        module = action
        for i in dir(module):
            if i.startswith("__"):
                continue
            pictures = getattr(module, i)
            self.picturesList.append(pictures)

    def createQpixmap(self):
        for indexI, i in enumerate(self.picturesList):
            for indexJ, j in enumerate(i):
                self.picturesList[indexI][indexJ] = QPixmap(str(self.imgDir / j))

    def getAllAction(self):
        self.createPicture()
        self.createQpixmap()
        return self.picturesList