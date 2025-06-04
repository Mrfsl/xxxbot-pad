#!/bin/bash
set -e

# 启动系统Redis服务
echo "启动系统Redis服务..."
redis-server /etc/redis/redis.conf --daemonize yes

# 等待系统Redis服务启动
echo "等待系统Redis服务可用..."
sleep 2

# 注释：已移除端口6378的Redis服务启动代码，统一使用系统Redis服务（端口6379）
echo "系统将只使用端口6379的Redis服务"

# 检查并确保3000端口可用
echo "检查终端服务端口..."
# 使用lsof检查端口是否被占用
if lsof -i:3000 > /dev/null 2>&1; then
    echo "警告：端口3000已被占用，尝试终止占用进程..."
    kill -9 $(lsof -t -i:3000) 2>/dev/null || true
    sleep 1
fi

# 启动WeTTy终端服务 - 使用/wetty作为基础路径
echo "启动WeTTy终端服务..."
# 使用完整路径或者尝试多种可能的路径
if command -v wetty &> /dev/null; then
    wetty --port 3000 --host 0.0.0.0 --allow-iframe --base /wetty --command /bin/bash &
elif [ -f "/usr/local/bin/wetty" ]; then
    /usr/local/bin/wetty --port 3000 --host 0.0.0.0 --allow-iframe --base /wetty --command /bin/bash &
elif [ -f "/usr/bin/wetty" ]; then
    /usr/bin/wetty --port 3000 --host 0.0.0.0 --allow-iframe --base /wetty --command /bin/bash &
else
    echo "警告：wetty命令未找到，跳过启动WeTTy终端服务"
fi

# 等待WeTTy服务启动
echo "等待WeTTy服务可用..."
sleep 3

# 注释: 不再单独启动管理后台服务器，由main.py统一管理
# 管理后台将由main.py自动启动，使用main_config.toml中配置的端口

# 读取协议版本配置
echo "读取协议版本配置..."
PROTOCOL_VERSION="849"  # 默认使用849协议
FRAMEWORK_TYPE="default"  # 默认使用默认框架

# 检查配置文件是否存在
if [ -f "/app/main_config.toml" ]; then
    # 提取协议版本
    EXTRACTED_VERSION=$(grep -A 5 '\[Protocol\]' /app/main_config.toml | grep 'version' | awk -F '"' '{print $2}')
    
    if [ ! -z "$EXTRACTED_VERSION" ]; then
        PROTOCOL_VERSION="$EXTRACTED_VERSION"
        echo "从配置文件中提取到协议版本: $PROTOCOL_VERSION"
    else
        echo "未从配置文件中提取到协议版本，使用默认值: $PROTOCOL_VERSION"
    fi
    
    # 提取框架类型
    FRAMEWORK_TYPE=$(grep -A 5 '\[Framework\]' /app/main_config.toml | grep 'type' | awk -F '"' '{print $2}')
    
    if [ ! -z "$FRAMEWORK_TYPE" ]; then
        echo "从配置文件中提取到框架类型: $FRAMEWORK_TYPE"
    else
        echo "未从配置文件中提取到框架类型，使用默认值: $FRAMEWORK_TYPE"
    fi
fi

# 打印协议版本信息，包括字符长度和十六进制表示
echo "使用协议版本: '$PROTOCOL_VERSION'"
echo "协议版本字符长度: ${#PROTOCOL_VERSION}"
if command -v hexdump &> /dev/null; then
    echo "协议版本十六进制表示: $(echo -n "$PROTOCOL_VERSION" | hexdump -C)"
else
    echo "协议版本十六进制表示: (hexdump命令不可用)"
fi

# 清理可能的空格和不可见字符
CLEAN_VERSION=$(echo "$PROTOCOL_VERSION" | tr -d '[:space:]')
echo "清理后的协议版本: '$CLEAN_VERSION'"

# 根据协议版本选择不同的服务路径
# 使用更严格的比较方式
if [[ "$CLEAN_VERSION" == "855" ]]; then
    # 855版本使用pad2目录
    PAD_SERVICE_PATH="/app/849/pad2/linuxService"
    echo "使用855协议服务路径: $PAD_SERVICE_PATH"
elif [[ "$CLEAN_VERSION" == "ipad" ]]; then
    # ipad版本使用pad3目录
    PAD_SERVICE_PATH="/app/849/pad3/linuxService"
    echo "使用iPad协议服务路径: $PAD_SERVICE_PATH"
elif [[ "$CLEAN_VERSION" == "Mac" ]]; then
    # Mac版本使用pad3目录(与iPad相同的目录)
    PAD_SERVICE_PATH="/app/849/pad3/linuxService"
    echo "使用Mac协议服务路径: $PAD_SERVICE_PATH"
else
    # 默认使用849协议路径
    PAD_SERVICE_PATH="/app/849/pad/linuxService"
    echo "使用849协议服务路径: $PAD_SERVICE_PATH"
fi

# 读取框架类型
FRAMEWORK_TYPE="default"
if [ -f "/app/main_config.toml" ]; then
    FRAMEWORK_TYPE=$(grep -A 5 '\[Framework\]' /app/main_config.toml | grep 'type' | awk -F '"' '{print $2}')
fi

if [[ "$FRAMEWORK_TYPE" == "wechat" ]]; then
    echo "仅作为API客户端（Client2），不启动849协议服务"
else
    # 启动pad服务（协议服务）
    echo "启动pad服务（协议服务）..."
    if [ -f "$PAD_SERVICE_PATH" ]; then
        # 在Linux系统上确保文件有执行权限
        chmod +x "$PAD_SERVICE_PATH"

        # 使用nohup在后台启动linuxService
        nohup "$PAD_SERVICE_PATH" > /app/logs/pad_service.log 2>&1 &

        # 记录进程号
        PAD_PID=$!
        echo "pad服务已启动，进程ID: $PAD_PID"

        # 等待pad服务启动
        echo "等待pad服务启动..."
        # 等待短暂停，给pad服务一些初始化时间
        sleep 2

        # 尝试最多5次，每次间隔短一些
        for i in {1..5}; do
            if curl -s http://127.0.0.1:9011 > /dev/null 2>&1 || curl -s http://127.0.0.1:9011/VXAPI/Login/GetQR > /dev/null 2>&1; then
                echo "pad服务已启动并可用"
                break
            else
                if [ $i -lt 5 ]; then
                    echo "等待pad服务启动，尝试 $i/5..."
                    sleep 1
                else
                    echo "警告：pad服务可能未完全启动，继续启动主应用..."
                fi
            fi
        done
    else
        echo "警告：pad服务文件不存在: $PAD_SERVICE_PATH"
    fi
fi

# 根据框架类型选择启动哪个框架
if [[ "$FRAMEWORK_TYPE" == "dow" ]]; then
    # 使用dow框架
    DOW_FRAMEWORK_PATH="/app/dow"
    echo "选择使用dow框架: $DOW_FRAMEWORK_PATH"
    
    if [ -d "$DOW_FRAMEWORK_PATH" ]; then
        echo "直接启动dow框架..."
        # 检查app.py是否存在
        if [ -f "$DOW_FRAMEWORK_PATH/app.py" ]; then
            cd "$DOW_FRAMEWORK_PATH"
            
            # 同时启动admin后台
            echo "正在启动admin后台界面..."
            cd /app
            python /app/admin/run_server.py &
            ADMIN_PID=$!
            echo "Admin后台已启动，进程ID: $ADMIN_PID"
            
            # 切回dow目录并启动app.py
            cd "$DOW_FRAMEWORK_PATH"
            echo "启动app.py..."
            exec python app.py
        else
            echo "警告：未找到dow框架的app.py"
            # 如果dow框架不存在，启动默认框架
            echo "启动默认框架..."
            exec python /app/main.py
        fi
    else
        echo "警告：dow框架目录不存在: $DOW_FRAMEWORK_PATH"
        # 如果dow框架目录不存在，启动默认框架
        echo "启动默认框架..."
        exec python /app/main.py
    fi
elif [[ "$FRAMEWORK_TYPE" == "dual" ]]; then
    # 双框架模式：先启动原始框架，等待登录成功后再启动DOW框架
    echo "选择使用双框架模式：先启动原始框架，登录成功后再启动DOW框架"
    
    # 准备两个框架路径
    DOW_FRAMEWORK_PATH="/app/dow"
    ORIGINAL_FRAMEWORK_PATH="/app"
    
    # 检查框架目录是否存在
    if [ ! -d "$DOW_FRAMEWORK_PATH" ]; then
        echo "警告：DOW框架目录不存在: $DOW_FRAMEWORK_PATH，将只启动原始框架"
        echo "启动默认框架..."
        exec python /app/main.py
    fi
    
    # 启动原始框架
    echo "启动原始框架..."
    cd $ORIGINAL_FRAMEWORK_PATH
    python /app/main.py &
    ORIGINAL_PID=$!
    echo "原始框架已启动，进程ID: $ORIGINAL_PID"
    
    # 启动消息回调守护进程
    echo "等待3秒后启动消息回调守护进程..."
    sleep 3
    echo "启动消息回调守护进程..."
    cd $ORIGINAL_FRAMEWORK_PATH
    python /app/wx849_callback_daemon.py &
    CALLBACK_PID=$!
    echo "消息回调守护进程已启动，进程ID: $CALLBACK_PID"
    
    # 等待原始框架登录成功
    echo "等待原始框架登录成功..."
    # 定义可能的robot_stat文件路径
    POSSIBLE_PATHS=(
        "/app/resource/robot_stat.json"
        "/app/resource/robot_stat.json"
        "/resource/robot_stat.json"
        "/app/resource/robot-stat.json"
        "/app/robot_stat.json"
    )
    
    # 检查实际文件路径
    ROBOT_STAT_FILE=""
    for path in "${POSSIBLE_PATHS[@]}"; do
        if [ -f "$path" ]; then
            ROBOT_STAT_FILE="$path"
            echo "找到robot_stat.json文件: $ROBOT_STAT_FILE"
            break
        fi
    done
    
    # 如果没有找到文件，使用默认路径
    if [ -z "$ROBOT_STAT_FILE" ]; then
        ROBOT_STAT_FILE="/app/resource/robot_stat.json"
        echo "未找到robot_stat.json文件，使用默认路径: $ROBOT_STAT_FILE"
    fi
    
    MAX_WAIT_TIME=300  # 最大等待时间(秒)
    WAIT_TIME=0
    
    while [ $WAIT_TIME -lt $MAX_WAIT_TIME ]; do
        # 检查是否存在手动启动信号
        if [ -f "/app/force_start_dow" ]; then
            echo "检测到手动启动信号，跳过等待直接启动DOW框架"
            break
        fi
        
        # 检查robot_stat.json是否存在且包含wxid
        if [ -f "$ROBOT_STAT_FILE" ]; then
            # 使用更灵活的方式提取wxid，兼容多种格式
            WXID=$(grep -o '"wxid"[^,]*' $ROBOT_STAT_FILE | cut -d':' -f2 | tr -d '"' | tr -d ' ')
            if [ ! -z "$WXID" ]; then
                echo "检测到原始框架已登录成功，wxid: $WXID"
                break
            else
                # 如果上面的方法失败，尝试另一种格式
                WXID=$(grep -o '"wxid"[ ]*:[ ]*"[^"]*"' $ROBOT_STAT_FILE | grep -o '"[^"]*"' | tail -1 | tr -d '"')
                if [ ! -z "$WXID" ]; then
                    echo "检测到原始框架已登录成功，wxid: $WXID (第二种格式)"
                    break
                fi
            fi
            
            # 显示文件内容，帮助调试
            echo "robot_stat.json内容:"
            cat $ROBOT_STAT_FILE
        else
            echo "robot_stat.json文件不存在，继续等待..."
        fi
        
        # 等待5秒后再次检查
        sleep 5
        WAIT_TIME=$((WAIT_TIME + 5))
        echo "等待原始框架登录中... ${WAIT_TIME}/${MAX_WAIT_TIME}秒"
    done
    
    if [ $WAIT_TIME -ge $MAX_WAIT_TIME ]; then
        echo "等待原始框架登录超时，DOW框架将不会启动"
        # 继续等待原始框架运行
        wait $ORIGINAL_PID
        exit 1
    fi
    
    # 原始框架登录成功，启动DOW框架
    echo "原始框架已登录成功，开始启动DOW框架..."
    cd $DOW_FRAMEWORK_PATH
    
    # 确保DOW框架配置正确
    # 检查配置文件是否存在
    if [ -f "$DOW_FRAMEWORK_PATH/config.json" ]; then
        # 可以在这里添加修改DOW配置的代码
        echo "DOW框架配置文件已存在"
    fi
    
    # 启动DOW框架
    echo "启动DOW框架..."
    python $DOW_FRAMEWORK_PATH/app.py &
    DOW_PID=$!
    echo "DOW框架已启动，进程ID: $DOW_PID"
    
    # 等待所有进程结束
    wait $ORIGINAL_PID $DOW_PID
else
    # 使用默认框架
    echo "使用默认框架..."
    
    # 启动主应用
    echo "启动XXXBot主应用..."
    exec python /app/main.py
fi