From work_askQiao.md 10.4 Q1
# 重新安装alfabet-lite解决运行环境问题


## 1. 重插硬盘
-> 扶正cwd，可恶mac老是自动退出我的外接磁盘，重新设置了
sudo pmset -a sleep 0
sudo pmset -a disksleep 0
**-> 长时间跑代码重开电脑时启用**
查看系统硬盘设置：pmset -g

System-wide power settings:
Currently in use:
 standby              0 # 关闭“待机模式”。mac 默认会在长时间不动后进入深度睡眠
 Sleep On Power Button 1
 autorestart          0
 powernap             1 # 系统休眠时仍允许处理后台任务（如邮件、iCloud）
 networkoversleep     0
 disksleep            0 # 永不让磁盘休眠
 sleep                0 (sleep prevented by powerd, sharingd, bluetoothd) # 不会整体休眠或断电外设
 ttyskeepawake        1 # 确保有终端活动时不睡
 displaysleep         60 # 显示器 60 分钟后可关闭
 tcpkeepalive         1 # 睡眠时保持 TCP 网络活动（如 SSH、AirDrop）
 powermode            0
 womp                 1 # 远程唤醒

---
## 2. 卸载 NREL/alfabet.git@0.2.2
python -m pip uninstall -y alfabet alfabet-lite
python -m pip cache purge # 清空 pip 的下载缓存区: （旧 wheel 包、源码压缩包、索引信息等）

## 3. 确认/安装正确的 TensorFlow
Mac mini（M 系列，已知 M4）。想要 GPU 加速：
    必须装 tensorflow-macos（苹果芯片版 TensorFlow 主体）-> 为 Apple Silicon 编译，提供 API 和 CPU 执行
    再装 tensorflow-metal（Metal 后端插件，负责把 TF 的算子跑在 Apple GPU 上）
    只装 tensorflow-macos ⇒ 也能用，但仅 CPU。

-> 存在冲突的版本得删
**-> 见环境时一开始就得考虑到从python->>最终包里所有版本都不能冲突**
->> 在terminal还是notebook里跑安装代码：见codetips.md

## 4. 安装alfabet-lite
直接装fork
python -m pip install --no-cache-dir "git+https://github.com/kangqiao-ctrl/alfabet_lite.git"

验证：import alfabet_lite as al
al.__file__
