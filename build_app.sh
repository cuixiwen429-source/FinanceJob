#!/bin/bash
# FinanceJob .app 构建脚本
# 生成 Dock 可识别的 macOS 应用包

set -e

APP_DIR="FinanceJob.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

echo "🔨 Building FinanceJob.app..."

# 1. 编译 C 启动器
echo "   Compiling launcher..."
cc -o "$MACOS/FinanceJobLauncher" "$MACOS/launcher.c" \
   -framework Foundation -framework AppKit

# 2. 生成图标
echo "   Generating icons..."
python3 -c "
from PIL import Image, ImageDraw, ImageFont
import os

size = 1024
img = Image.new('RGBA', (size, size), (0,0,0,0))
draw = ImageDraw.Draw(img)
for i in range(size):
    r,g,b = int(15+i/size*30), int(30+i/size*50), int(70+i/size*80)
    draw.rectangle([0,i,size,i+1], fill=(r,g,b,255))
mask = Image.new('L',(size,size),0)
ImageDraw.Draw(mask).rounded_rectangle([20,20,size-20,size-20], radius=180, fill=255)
try:
    f1 = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',420,index=1)
except: f1 = ImageFont.load_default()
draw.text((size//2,size//2-60),'FJ',fill=(16,185,129,255),font=f1,anchor='mm')
try:
    f2 = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc',120)
except: f2 = ImageFont.load_default()
draw.text((size//2,size//2+260),'求职',fill=(255,255,255,220),font=f2,anchor='mm')
result = Image.new('RGBA',(size,size),(0,0,0,0))
result.paste(img,(0,0),mask)
iconset = '$RESOURCES/FinanceJob.iconset'
os.makedirs(iconset, exist_ok=True)
for name,s in {'icon_16x16.png':16,'icon_16x16@2x.png':32,'icon_32x32.png':32,'icon_32x32@2x.png':64,'icon_128x128.png':128,'icon_128x128@2x.png':256,'icon_256x256.png':256,'icon_256x256@2x.png':512,'icon_512x512.png':512,'icon_512x512@2x.png':1024}.items():
    result.resize((s,s), Image.LANCZOS).save(f'{iconset}/{name}')
os.system(f'iconutil -c icns {iconset} -o $RESOURCES/FinanceJob.icns')
print('✅ Icons generated')
"

# 3. 签名
echo "   Code signing..."
codesign --force --sign - "$APP_DIR" 2>/dev/null || echo "   (ad-hoc signed)"

# 4. 验证
echo "   Verifying..."
plutil -lint "$CONTENTS/Info.plist" 2>/dev/null

echo ""
echo "✅ FinanceJob.app 构建完成!"
echo "   路径: $(pwd)/$APP_DIR"
echo ""
echo "   双击启动，或拖入 Dock 使用"
echo ""
echo "   命令行启动: open $APP_DIR"
