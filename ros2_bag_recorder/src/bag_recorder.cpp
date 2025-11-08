#include <memory>
#include <string>
#include <vector>
#include <csignal>
#include <chrono>

#include "rclcpp/rclcpp.hpp"
#include "rosbag2_transport/recorder.hpp"
#include "rosbag2_cpp/writer.hpp"
#include "rosbag2_storage/storage_options.hpp"

using namespace std::chrono_literals;

/**
 * High-performance ROS2 bag recorder using rosbag2_transport
 * 
 * This uses the official rosbag2_transport::Recorder class which provides:
 * - Multi-threaded message handling
 * - Efficient buffering and storage
 * - Performance optimizations (same as ros2 bag record)
 * - Support for compression, splitting, filtering, etc.
 */
class BagRecorderNode : public rclcpp::Node
{
public:
  BagRecorderNode()
  : Node("bag_recorder")
  {
    // Declare parameters
    this->declare_parameter<std::string>("bag_path", "bag_recording");
    this->declare_parameter<std::vector<std::string>>("topics", std::vector<std::string>());
    this->declare_parameter<std::string>("storage_id", "sqlite3");
    this->declare_parameter<bool>("all_topics", false);
    this->declare_parameter<bool>("all_topics_except", false);
    this->declare_parameter<std::vector<std::string>>("excluded_topics", std::vector<std::string>());
    this->declare_parameter<std::string>("compression_mode", "none");  // none, file, message
    this->declare_parameter<std::string>("compression_format", "");   // zstd, lz4
    this->declare_parameter<uint64_t>("max_bag_size", 0);  // 0 means unlimited (in MB)
    this->declare_parameter<uint64_t>("max_bag_duration", 0);  // 0 means unlimited (in seconds)
    this->declare_parameter<uint64_t>("max_cache_size", 0);  // 0 means use default
    this->declare_parameter<std::string>("storage_config_file", "");

    // Get parameters
    std::string bag_path = this->get_parameter("bag_path").as_string();
    std::vector<std::string> topics = this->get_parameter("topics").as_string_array();
    std::string storage_id = this->get_parameter("storage_id").as_string();
    bool all_topics = this->get_parameter("all_topics").as_bool();
    bool all_topics_except = this->get_parameter("all_topics_except").as_bool();
    std::vector<std::string> excluded_topics = this->get_parameter("excluded_topics").as_string_array();
    std::string compression_mode = this->get_parameter("compression_mode").as_string();
    std::string compression_format = this->get_parameter("compression_format").as_string();
    uint64_t max_bag_size = this->get_parameter("max_bag_size").as_uint();
    uint64_t max_bag_duration = this->get_parameter("max_bag_duration").as_uint();
    uint64_t max_cache_size = this->get_parameter("max_cache_size").as_uint();
    std::string storage_config_file = this->get_parameter("storage_config_file").as_string();

    // Configure storage options
    rosbag2_storage::StorageOptions storage_options;
    storage_options.uri = bag_path;
    storage_options.storage_id = storage_id;
    storage_options.max_bagfile_size = max_bag_size * 1024 * 1024;  // Convert MB to bytes
    if (!storage_config_file.empty()) {
      storage_options.storage_config_uri = storage_config_file;
    }

    // Configure record options
    rosbag2_transport::RecordOptions record_options;
    
    if (all_topics) {
      record_options.all_topics = true;
      RCLCPP_INFO(this->get_logger(), "Recording all topics");
    } else if (all_topics_except) {
      record_options.all_topics = true;
      record_options.excluded_topics = excluded_topics;
      RCLCPP_INFO(this->get_logger(), "Recording all topics except %zu excluded topics", 
                  excluded_topics.size());
    } else {
      record_options.topics = topics;
      RCLCPP_INFO(this->get_logger(), "Recording %zu specified topics", topics.size());
    }

    // Compression settings
    if (compression_mode != "none") {
      record_options.compression_mode = compression_mode;
      if (!compression_format.empty()) {
        record_options.compression_format = compression_format;
      }
      RCLCPP_INFO(this->get_logger(), "Compression: mode=%s, format=%s", 
                  compression_mode.c_str(), compression_format.c_str());
    }

    // Duration limit
    if (max_bag_duration > 0) {
      record_options.max_bagfile_duration = std::chrono::seconds(max_bag_duration);
      RCLCPP_INFO(this->get_logger(), "Max bag duration: %lu seconds", max_bag_duration);
    }

    // Cache size
    if (max_cache_size > 0) {
      record_options.max_cache_size = max_cache_size;
      RCLCPP_INFO(this->get_logger(), "Max cache size: %lu MB", max_cache_size);
    }

    // Create recorder using rosbag2_transport (official high-performance implementation)
    recorder_ = std::make_shared<rosbag2_transport::Recorder>(
      std::make_unique<rosbag2_cpp::Writer>());

    // Start recording
    try {
      recorder_->record(storage_options, record_options);
      RCLCPP_INFO(this->get_logger(), "Recording started to: %s", bag_path.c_str());
    } catch (const std::exception& e) {
      RCLCPP_ERROR(this->get_logger(), "Failed to start recording: %s", e.what());
      rclcpp::shutdown();
      return;
    }

    // Setup shutdown handler
    shutdown_timer_ = this->create_wall_timer(
      100ms, [this]() {
        if (!rclcpp::ok()) {
          RCLCPP_INFO(this->get_logger(), "Shutting down recorder...");
          recorder_.reset();
        }
      });
  }

  ~BagRecorderNode()
  {
    if (recorder_) {
      recorder_.reset();
      RCLCPP_INFO(this->get_logger(), "Recorder stopped");
    }
  }

private:
  std::shared_ptr<rosbag2_transport::Recorder> recorder_;
  rclcpp::TimerBase::SharedPtr shutdown_timer_;
};

// Global signal handler
std::shared_ptr<BagRecorderNode> g_node = nullptr;

void signal_handler(int signal)
{
  if (g_node) {
    RCLCPP_INFO(rclcpp::get_logger("bag_recorder"), 
                "Received signal %d, shutting down...", signal);
    rclcpp::shutdown();
  }
}

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);

  // Register signal handlers
  signal(SIGINT, signal_handler);
  signal(SIGTERM, signal_handler);

  g_node = std::make_shared<BagRecorderNode>();

  if (!g_node) {
    RCLCPP_ERROR(rclcpp::get_logger("bag_recorder"), "Failed to create recorder node");
    return 1;
  }

  // Spin until shutdown
  rclcpp::spin(g_node);

  g_node.reset();
  rclcpp::shutdown();

  return 0;
}
