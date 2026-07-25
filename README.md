# 桌面宠物 Python实现
基于 Python + PyQt5 开发的交互式桌面萌宠

## 📖 程序说明
桌宠默认每10秒自动播放一组动画动作
- 鼠标**双击左键**：激活自动行走功能
- 行走状态单击左键：取消行走
- **鼠标右键呼出功能菜单**，后续持续增加更多快捷功能

> 默认动画素材转载自微博 @XGBGHOST
> 你可以自行替换图片素材，自由新增、删减动画动作

## ✨ 新增拓展功能
### 📱 右键菜单：一键打开微信（Windows）
点击菜单无法正常启动微信，一般是微信安装路径不一致，请手动修改配置：
打开文件 `core/ability.py`
找到微信路径代码：
```python
wechat_path = r"C:\Program Files\Tencent\Weixin\Weixin.exe"

获取本机微信真实路径
桌面微信快捷方式右键 →【属性】
复制【目标】一栏完整路径，替换上面代码内路径即可
⚙️ 环境、运行与打包方法
运行环境：Python3.7 + PyQt5
▶️ 运行方式
bash
运行
# 基础启动
python run.py

# 使用非守护进程方式启动
python run.py --daemon

# 启动并开启托盘功能（推荐）
python run.py --tray

📦 打包命令
bash
运行
pyinstaller run.spec

说明：打包配置仅在 Mac 上测试通过，Windows 平台适配情况未知
📂 文件说明
core/action.py
配置桌宠全部动画动作，动画素材图片存放于 img 文件夹。
你可以自由新增 / 删减动作：将每一帧图片放入img文件夹，再在action.py中配置对应路径，程序会自动读取加载。
core/settings.py 全局配置参数
yaml
MOVIE_TIME_INTERVAL: 每个动画的播放间隔，单位 秒
INIT_PICTURE: 桌宠静止时默认的图片
TRAY_ICON: 系统托盘的图标
ICON: 程序窗口图标
MOUSE_TO_LEFT_*: 鼠标左滑时的动作，一共三帧
MOUSE_TO_RIGHT_*: 鼠标右滑时的动作，一共三帧
WALK: 行走的动作，一共2帧，多余帧不会播放

💬 联系方式
如果你有新的功能想法，或是运行程序遇到问题，欢迎联系！
邮箱：19821620659@163.com
plaintext

### 使用步骤
1. GitHub编辑页面按 `Ctrl + A` 选中全部旧内容，删除
2. 复制上面整块文本粘贴进去
3. 底部填写提交信息：`docs:重构美化README，新增微信启动功能说明，更新联系方式`
4. 点击 Commit changes

粘贴后点上方【Preview】，就能预览最终成品效果。
