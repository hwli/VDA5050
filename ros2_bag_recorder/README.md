# ROS2 高性能录包程序

基于 `rosbag2_transport::Recorder` 的高性能 ROS2 录包工具，性能与原生 `ros2 bag record` 相当或更优。

## 特性

- ✅ **使用官方高性能接口**：基于 `rosbag2_transport::Recorder`，与原生工具使用相同的优化实现
- ✅ **多线程异步处理**：内置消息缓冲和多线程写入
- ✅ **完整功能支持**：支持压缩、分割、过滤等所有原生功能
- ✅ **参数化配置**：通过 ROS2 参数灵活配置
- ✅ **性能保证**：不亚于原生 `ros2 bag record` 的性能

## 编译

```bash
# 在 ROS2 工作空间根目录
colcon build --packages-select ros2_bag_recorder
source install/setup.bash
```

## 使用方法

### 1. 录制指定话题

```bash
ros2 run ros2_bag_recorder bag_recorder \
  --ros-args \
  -p bag_path:=my_recording \
  -p topics:="['/camera/image', '/lidar/points', '/odom']"
```

### 2. 录制所有话题

```bash
ros2 run ros2_bag_recorder bag_recorder \
  --ros-args \
  -p bag_path:=my_recording \
  -p all_topics:=true
```

### 3. 录制所有话题（排除某些话题）

```bash
ros2 run ros2_bag_recorder bag_recorder \
  --ros-args \
  -p bag_path:=my_recording \
  -p all_topics_except:=true \
  -p excluded_topics:="['/rosout', '/parameter_events']"
```

### 4. 启用压缩

```bash
ros2 run ros2_bag_recorder bag_recorder \
  --ros-args \
  -p bag_path:=my_recording \
  -p topics:="['/camera/image']" \
  -p compression_mode:=file \
  -p compression_format:=zstd
```

### 5. 设置最大文件大小和时长

```bash
ros2 run ros2_bag_recorder bag_recorder \
  --ros-args \
  -p bag_path:=my_recording \
  -p topics:="['/camera/image']" \
  -p max_bag_size:=1000 \
  -p max_bag_duration:=3600
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `bag_path` | string | "bag_recording" | 输出 bag 文件路径 |
| `topics` | string[] | [] | 要录制的话题列表 |
| `storage_id` | string | "sqlite3" | 存储后端（sqlite3/mcap） |
| `all_topics` | bool | false | 是否录制所有话题 |
| `all_topics_except` | bool | false | 是否录制所有话题（排除列表） |
| `excluded_topics` | string[] | [] | 排除的话题列表 |
| `compression_mode` | string | "none" | 压缩模式：none/file/message |
| `compression_format` | string | "" | 压缩格式：zstd/lz4 |
| `max_bag_size` | uint64 | 0 | 最大文件大小（MB，0=无限制） |
| `max_bag_duration` | uint64 | 0 | 最大录制时长（秒，0=无限制） |
| `max_cache_size` | uint64 | 0 | 最大缓存大小（MB，0=使用默认值） |
| `storage_config_file` | string | "" | 存储配置文件路径 |

## 性能对比

本程序使用 `rosbag2_transport::Recorder`，与原生 `ros2 bag record` 使用相同的底层实现，因此：

- **性能相同或更优**：使用相同的优化代码
- **功能完整**：支持所有原生功能
- **代码更简洁**：只需配置参数，无需实现底层逻辑

## 停止录制

按 `Ctrl+C` 优雅停止，程序会确保所有缓冲消息写入磁盘。

## 示例场景

### 录制相机和激光雷达数据

```bash
ros2 run ros2_bag_recorder bag_recorder \
  --ros-args \
  -p bag_path:=sensor_data \
  -p topics:="['/camera/color/image_raw', '/camera/depth/image_raw', '/velodyne_points']" \
  -p compression_mode:=file \
  -p compression_format:=zstd
```

### 长时间录制（自动分割）

```bash
ros2 run ros2_bag_recorder bag_recorder \
  --ros-args \
  -p bag_path:=long_recording \
  -p all_topics:=true \
  -p max_bag_size:=5000 \
  -p max_bag_duration:=7200
```

## 技术细节

- **底层库**：`rosbag2_transport::Recorder`
- **存储格式**：SQLite3（默认）或 MCAP
- **序列化格式**：CDR
- **多线程**：自动管理，无需手动配置

## 与原生工具的区别

| 特性 | ros2 bag record | 本程序 |
|------|----------------|--------|
| 命令行参数 | 是 | ROS2 参数 |
| 性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 可编程性 | 低 | 高 |
| 集成到节点 | 否 | 是 |

## 故障排除

### 编译错误：找不到 rosbag2_transport

确保已安装 ROS2 完整版：
```bash
sudo apt install ros-<distro>-rosbag2-transport
```

### 录制失败：权限问题

确保输出目录有写权限：
```bash
chmod 755 /path/to/output/directory
```

### 性能问题

- 使用 SSD 存储
- 启用压缩（对于大消息）
- 调整 `max_cache_size` 参数
