#!/bin/bash
# build_deb.sh — 把 MyOS 打包成 .deb 安装包
#
# 用法：
#     bash packaging/build_deb.sh            # 版本号默认 1.0.0
#     bash packaging/build_deb.sh 1.2.0      # 指定版本号
#
# 产物：packaging/build/myos_<版本>_amd64.deb
#
# 说明：deb 只装应用自身（几 MB）；ROS Noetic 通过 apt 依赖声明，
#       PySide6 由使用者在安装后手动 pip 安装（见 DEBIAN/postinst 提示）。
#
# 依赖工具：dpkg-deb（Ubuntu 自带，无需安装 debhelper）

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="$(dirname "$HERE")"

PKG_NAME=myos
VERSION="${1:-1.0.0}"
ARCH=amd64

# 应用图标（换成 style/icon 下想要的图片即可）
APP_ICON="style/icon/nailong.png"

# 需要打进 deb 的项目内容
APP_FILES=(
    main.py
    myos_config.py
    requirements.txt
    README.md
    ui
    ros_bridge
    param_store
    config
    sh
    style
)

BUILD="$HERE/build/${PKG_NAME}_${VERSION}_${ARCH}"
OUT="$HERE/build/${PKG_NAME}_${VERSION}_${ARCH}.deb"

echo "[1/4] 清理并组装目录树: $BUILD"
rm -rf "$BUILD"
mkdir -p "$BUILD/opt/$PKG_NAME"

# ---- 应用本体 → /opt/myos ----
for f in "${APP_FILES[@]}"; do
    if [ -e "$PROJ/$f" ]; then
        cp -r "$PROJ/$f" "$BUILD/opt/$PKG_NAME/"
    else
        echo "      跳过不存在的文件: $f"
    fi
done

# 清掉字节码缓存（换机器/换 Python 版本时无用且会干扰）
find "$BUILD/opt/$PKG_NAME" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$BUILD/opt/$PKG_NAME" -name '*.pyc' -delete
# sh 脚本保留可执行权限（程序里用 bash 调用，这里只是保持一致）
chmod +x "$BUILD/opt/$PKG_NAME"/sh/*.sh 2>/dev/null || true

# ---- 启动器 / 应用菜单 / 图标 ----
echo "[2/4] 安装启动器与桌面入口"
mkdir -p "$BUILD/usr/bin" \
         "$BUILD/usr/share/applications" \
         "$BUILD/usr/share/pixmaps"
cp "$HERE/usr/bin/myos" "$BUILD/usr/bin/myos"
cp "$HERE/usr/share/applications/myos.desktop" "$BUILD/usr/share/applications/"
if [ -f "$PROJ/$APP_ICON" ]; then
    cp "$PROJ/$APP_ICON" "$BUILD/usr/share/pixmaps/myos.png"
else
    echo "      警告: 未找到图标 $APP_ICON，桌面图标将使用默认样式"
fi

# ---- DEBIAN 控制信息（注入版本号与安装体积）----
echo "[3/4] 生成控制信息"
mkdir -p "$BUILD/DEBIAN"
sed "s/@VERSION@/$VERSION/" "$HERE/DEBIAN/control" > "$BUILD/DEBIAN/control"
cp "$HERE/DEBIAN/postinst" "$HERE/DEBIAN/postrm" "$BUILD/DEBIAN/"
echo "Installed-Size: $(du -sk "$BUILD" | cut -f1)" >> "$BUILD/DEBIAN/control"

# ---- 权限统一：目录 755、可执行脚本 755、普通文件 644 ----
find "$BUILD" -type d -exec chmod 755 {} +
find "$BUILD" -type f -exec chmod 644 {} +
chmod 755 "$BUILD/usr/bin/myos" \
          "$BUILD/DEBIAN/postinst" "$BUILD/DEBIAN/postrm"
chmod 755 "$BUILD/opt/$PKG_NAME"/sh/*.sh 2>/dev/null || true

# ---- 打包 ----
echo "[4/4] 生成 deb: $OUT"
mkdir -p "$HERE/build"
# --root-owner-group: 文件属主统一为 root:root（无需 fakeroot）
dpkg-deb --build --root-owner-group "$BUILD" "$OUT"

echo
echo "完成: $OUT  ($(du -h "$OUT" | cut -f1))"
echo "安装: sudo dpkg -i \"$OUT\"   （依赖缺失时用 sudo apt -f install 补齐）"
echo "卸载: sudo dpkg -r $PKG_NAME"
