#include <chrono>
#include <memory>
#include <string>
#include <vector>
#include <thread>
#include <atomic>
#include <mutex>
#include <queue>
#include <condition_variable>

#include "rclcpp/rclcpp.hpp"
#include "rosbag2_cpp/writer.hpp"
#include "rosbag2_cpp/writers/sequential_writer.hpp"
#include "rosbag2_storage/storage_options.hpp"
#include "rosbag2_storage_default_plugins/sqlite/sqlite_storage.hpp"
#include "rosbag2_cpp/typesupport_helpers.hpp"
#include "rosbag2_cpp/serialization_format_converter_factory.hpp"
#include "rosbag2_cpp/serialization_format_converter_factory_interface.hpp"

#include "rcutils/types.h"
#include "rcpputils/shared_library.hpp"

using namespace std::chrono_literals;

/**
 * High-performance ROS2 bag recorder
 * 
 * Features:
 * - Multi-threaded message buffering for high throughput
 * - Efficient storage using SQLite3
 * - Low-latency subscription handling
 * - Configurable buffer size and topics
 */
class BagRecorder : public rclcpp::Node
{
public:
  BagRecorder()
  : Node("bag_recorder"),
    stop_recording_(false),
    messages_recorded_(0)
  {
    // Declare parameters
    this->declare_parameter<std::string>("bag_path", "bag_recording");
    this->declare_parameter<std::vector<std::string>>("topics", std::vector<std::string>());
    this->declare_parameter<std::string>("storage_id", "sqlite3");
    this->declare_parameter<int>("buffer_size", 1000);
    this->declare_parameter<bool>("all_topics", false);
    this->declare_parameter<int>("max_bag_size", 0);  // 0 means unlimited
    this->declare_parameter<int>("max_bag_duration", 0);  // 0 means unlimited (in seconds)

    // Get parameters
    std::string bag_path = this->get_parameter("bag_path").as_string();
    std::vector<std::string> topics = this->get_parameter("topics").as_string_array();
    std::string storage_id = this->get_parameter("storage_id").as_string();
    buffer_size_ = this->get_parameter("buffer_size").as_int();
    bool all_topics = this->get_parameter("all_topics").as_bool();
    max_bag_size_ = this->get_parameter("max_bag_size").as_int();
    max_bag_duration_ = this->get_parameter("max_bag_duration").as_int();

    // Initialize bag writer
    rosbag2_storage::StorageOptions storage_options;
    storage_options.uri = bag_path;
    storage_options.storage_id = storage_id;

    rosbag2_cpp::ConverterOptions converter_options;
    converter_options.input_serialization_format = "cdr";
    converter_options.output_serialization_format = "cdr";

    try {
      writer_ = std::make_unique<rosbag2_cpp::writers::SequentialWriter>();
      writer_->open(storage_options, converter_options);
      RCLCPP_INFO(this->get_logger(), "Opened bag file: %s", bag_path.c_str());
    } catch (const std::exception& e) {
      RCLCPP_ERROR(this->get_logger(), "Failed to open bag file: %s", e.what());
      rclcpp::shutdown();
      return;
    }

    // Discover topics if all_topics is true
    if (all_topics) {
      topics = discover_topics();
      RCLCPP_INFO(this->get_logger(), "Discovered %zu topics", topics.size());
    }

    if (topics.empty()) {
      RCLCPP_WARN(this->get_logger(), "No topics specified for recording");
      rclcpp::shutdown();
      return;
    }

    // Start recording thread
    recording_thread_ = std::thread(&BagRecorder::recording_loop, this);

    // Subscribe to topics
    for (const auto& topic : topics) {
      subscribe_to_topic(topic);
    }

    // Start statistics timer
    stats_timer_ = this->create_wall_timer(
      5s, std::bind(&BagRecorder::print_statistics, this));

    // Start duration check timer if needed
    if (max_bag_duration_ > 0) {
      duration_timer_ = this->create_wall_timer(
        1s, std::bind(&BagRecorder::check_duration, this));
      start_time_ = std::chrono::steady_clock::now();
    }

    RCLCPP_INFO(this->get_logger(), "Recording started on %zu topics", topics.size());
  }

  ~BagRecorder()
  {
    stop_recording_ = true;
    cv_.notify_all();
    
    if (recording_thread_.joinable()) {
      recording_thread_.join();
    }

    if (writer_) {
      writer_->close();
      RCLCPP_INFO(this->get_logger(), "Bag file closed. Total messages recorded: %lu", 
                  messages_recorded_.load());
    }
  }

private:
  struct MessageData
  {
    std::string topic_name;
    std::string type_name;
    rclcpp::SerializedMessage serialized_msg;
    rclcpp::Time timestamp;
  };

  void subscribe_to_topic(const std::string& topic_name)
  {
    // Get topic type
    auto topic_info = this->get_topic_names_and_types();
    std::string type_name;
    
    for (const auto& [name, types] : topic_info) {
      if (name == topic_name) {
        if (!types.empty()) {
          type_name = types[0];
          break;
        }
      }
    }

    if (type_name.empty()) {
      RCLCPP_WARN(this->get_logger(), "Could not determine type for topic: %s", 
                  topic_name.c_str());
      return;
    }

    // Create generic subscription
    auto subscription = this->create_generic_subscription(
      topic_name,
      type_name,
      rclcpp::QoS(10),
      [this, topic_name, type_name](std::shared_ptr<rclcpp::SerializedMessage> msg) {
        this->message_callback(topic_name, type_name, msg);
      }
    );

    subscriptions_.push_back(subscription);

    // Register topic in bag
    rosbag2_storage::TopicMetadata topic_metadata;
    topic_metadata.name = topic_name;
    topic_metadata.type = type_name;
    topic_metadata.serialization_format = "cdr";
    writer_->create_topic(topic_metadata);

    RCLCPP_INFO(this->get_logger(), "Subscribed to topic: %s [%s]", 
                topic_name.c_str(), type_name.c_str());
  }

  void message_callback(
    const std::string& topic_name,
    const std::string& type_name,
    std::shared_ptr<rclcpp::SerializedMessage> msg)
  {
    std::lock_guard<std::mutex> lock(buffer_mutex_);
    
    // Check buffer size
    if (message_buffer_.size() >= static_cast<size_t>(buffer_size_)) {
      // Buffer full, drop oldest message (or wait)
      // For high performance, we drop instead of blocking
      return;
    }

    MessageData data;
    data.topic_name = topic_name;
    data.type_name = type_name;
    data.serialized_msg = *msg;
    data.timestamp = this->now();

    message_buffer_.push(data);
    cv_.notify_one();
  }

  void recording_loop()
  {
    while (!stop_recording_ || !message_buffer_.empty()) {
      std::unique_lock<std::mutex> lock(buffer_mutex_);
      
      // Wait for messages or stop signal
      cv_.wait(lock, [this] {
        return !message_buffer_.empty() || stop_recording_;
      });

      // Process all available messages in batch for better performance
      std::queue<MessageData> batch;
      while (!message_buffer_.empty() && batch.size() < 100) {
        batch.push(message_buffer_.front());
        message_buffer_.pop();
      }
      lock.unlock();

      // Write messages to bag
      while (!batch.empty()) {
        auto& data = batch.front();
        
        rosbag2_storage::SerializedBagMessage bag_message;
        bag_message.topic_name = data.topic_name;
        bag_message.time_stamp = data.timestamp.nanoseconds();
        bag_message.serialized_data = std::make_shared<rcutils_uint8_array_t>();
        bag_message.serialized_data->buffer = 
          new uint8_t[data.serialized_msg.size()];
        bag_message.serialized_data->buffer_length = data.serialized_msg.size();
        bag_message.serialized_data->buffer_capacity = data.serialized_msg.size();
        memcpy(bag_message.serialized_data->buffer,
               data.serialized_msg.get_rcl_serialized_message().buffer,
               data.serialized_msg.size());

        try {
          writer_->write(bag_message);
          messages_recorded_++;
        } catch (const std::exception& e) {
          RCLCPP_ERROR(this->get_logger(), "Failed to write message: %s", e.what());
        }

        // Cleanup
        delete[] bag_message.serialized_data->buffer;
        bag_message.serialized_data->buffer = nullptr;

        batch.pop();
      }

      // Check bag size limit
      if (max_bag_size_ > 0 && messages_recorded_.load() >= static_cast<size_t>(max_bag_size_)) {
        RCLCPP_INFO(this->get_logger(), "Reached maximum bag size, stopping recording");
        stop_recording_ = true;
        rclcpp::shutdown();
        break;
      }
    }
  }

  void print_statistics()
  {
    auto recorded = messages_recorded_.load();
    RCLCPP_INFO(this->get_logger(), 
                "Statistics: %lu messages recorded, buffer size: %zu",
                recorded, message_buffer_.size());
  }

  void check_duration()
  {
    if (max_bag_duration_ > 0) {
      auto elapsed = std::chrono::steady_clock::now() - start_time_;
      auto elapsed_seconds = std::chrono::duration_cast<std::chrono::seconds>(elapsed).count();
      
      if (elapsed_seconds >= max_bag_duration_) {
        RCLCPP_INFO(this->get_logger(), "Reached maximum bag duration, stopping recording");
        stop_recording_ = true;
        rclcpp::shutdown();
      }
    }
  }

  std::vector<std::string> discover_topics()
  {
    std::vector<std::string> topics;
    auto topic_info = this->get_topic_names_and_types();
    
    for (const auto& [name, types] : topic_info) {
      // Filter out system topics
      if (name.find("/rosout") == std::string::npos &&
          name.find("/parameter_events") == std::string::npos &&
          name.find("/clock") == std::string::npos) {
        topics.push_back(name);
      }
    }
    
    return topics;
  }

  std::unique_ptr<rosbag2_cpp::writers::SequentialWriter> writer_;
  std::vector<rclcpp::GenericSubscription::SharedPtr> subscriptions_;
  
  std::queue<MessageData> message_buffer_;
  std::mutex buffer_mutex_;
  std::condition_variable cv_;
  std::thread recording_thread_;
  
  std::atomic<bool> stop_recording_;
  std::atomic<size_t> messages_recorded_;
  
  int buffer_size_;
  size_t max_bag_size_;
  int max_bag_duration_;
  std::chrono::steady_clock::time_point start_time_;
  
  rclcpp::TimerBase::SharedPtr stats_timer_;
  rclcpp::TimerBase::SharedPtr duration_timer_;
};

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  
  auto node = std::make_shared<BagRecorder>();
  
  // Handle SIGINT (Ctrl+C)
  signal(SIGINT, [](int) {
    RCLCPP_INFO(rclcpp::get_logger("bag_recorder"), "Received SIGINT, shutting down...");
    rclcpp::shutdown();
  });
  
  rclcpp::spin(node);
  rclcpp::shutdown();
  
  return 0;
}
