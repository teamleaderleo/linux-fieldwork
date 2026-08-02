#include <boost/asio.hpp>
#include <boost/asio/posix/stream_descriptor.hpp>
#include <curl/curl.h>

#include <chrono>
#include <cstdint>
#include <exception>
#include <iostream>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>

using namespace std::chrono_literals;
namespace asio = boost::asio;
using boost::system::error_code;

class SplitServer {
 public:
  SplitServer()
      : acceptor_(io_, {asio::ip::make_address("127.0.0.1"), 0}),
        port_(acceptor_.local_endpoint().port()),
        thread_([this] { run(); }) {}

  ~SplitServer() {
    if (thread_.joinable())
      thread_.join();
  }

  unsigned short port() const { return port_; }

 private:
  void run() noexcept {
    try {
      asio::ip::tcp::socket socket(io_);
      acceptor_.accept(socket);

      asio::streambuf request;
      asio::read_until(socket, request, "\r\n\r\n");

      static constexpr char first[] =
          "HTTP/1.1 200 OK\r\n"
          "Content-Length: 12\r\n"
          "Connection: close\r\n"
          "\r\n"
          "hello ";
      asio::write(socket, asio::buffer(first, sizeof(first) - 1));

      std::this_thread::sleep_for(350ms);

      static constexpr char second[] = "world!";
      asio::write(socket, asio::buffer(second, sizeof(second) - 1));
      socket.shutdown(asio::ip::tcp::socket::shutdown_both);
      socket.close();
    } catch (const std::exception& e) {
      std::cerr << "server: " << e.what() << '\n';
    }
  }

  asio::io_context io_;
  asio::ip::tcp::acceptor acceptor_;
  unsigned short port_;
  std::thread thread_;
};

class MultiClient {
 public:
  enum class Mode { OneShot, Rearm };

  struct Outcome {
    bool completed = false;
    bool timed_out = false;
    CURLcode result = CURLE_OK;
    std::string body;
    unsigned read_completions = 0;
  };

  explicit MultiClient(Mode mode)
      : mode_(mode),
        multi_(curl_multi_init()),
        easy_(curl_easy_init()),
        curl_timer_(io_),
        deadline_(io_) {
    if (!multi_ || !easy_)
      throw std::runtime_error("curl initialization failed");

    check_multi(curl_multi_setopt(multi_, CURLMOPT_SOCKETFUNCTION,
                                  &MultiClient::socket_callback));
    check_multi(curl_multi_setopt(multi_, CURLMOPT_SOCKETDATA, this));
    check_multi(curl_multi_setopt(multi_, CURLMOPT_TIMERFUNCTION,
                                  &MultiClient::timer_callback));
    check_multi(curl_multi_setopt(multi_, CURLMOPT_TIMERDATA, this));

    check_easy(curl_easy_setopt(easy_, CURLOPT_WRITEFUNCTION,
                                &MultiClient::write_callback));
    check_easy(curl_easy_setopt(easy_, CURLOPT_WRITEDATA, this));
    check_easy(curl_easy_setopt(easy_, CURLOPT_NOSIGNAL, 1L));
    check_easy(curl_easy_setopt(easy_, CURLOPT_HTTP_VERSION,
                                CURL_HTTP_VERSION_1_1));
    check_easy(curl_easy_setopt(easy_, CURLOPT_FRESH_CONNECT, 1L));
    check_easy(curl_easy_setopt(easy_, CURLOPT_FORBID_REUSE, 1L));
  }

  ~MultiClient() { cleanup(); }

  Outcome run(const std::string& url, std::chrono::milliseconds timeout) {
    check_easy(curl_easy_setopt(easy_, CURLOPT_URL, url.c_str()));
    check_multi(curl_multi_add_handle(multi_, easy_));
    added_ = true;

    deadline_.expires_after(timeout);
    deadline_.async_wait([this](const error_code& ec) {
      if (!ec && !outcome_.completed) {
        outcome_.timed_out = true;
        io_.stop();
      }
    });

    drive(CURL_SOCKET_TIMEOUT, 0);
    io_.run();
    cleanup();
    return outcome_;
  }

 private:
  struct Watch : std::enable_shared_from_this<Watch> {
    explicit Watch(MultiClient& owner, curl_socket_t fd)
        : owner(owner), fd(fd), descriptor(owner.io_, fd) {}

    ~Watch() {
      if (descriptor.is_open())
        (void)descriptor.release();
    }

    void update(int what) {
      ++generation;
      desired = what;
      error_code ec;
      descriptor.cancel(ec);
      read_pending = false;
      write_pending = false;
      arm();
    }

    void remove() {
      ++generation;
      desired = CURL_POLL_REMOVE;
      error_code ec;
      descriptor.cancel(ec);
      if (descriptor.is_open())
        (void)descriptor.release();
      read_pending = false;
      write_pending = false;
    }

    void arm() {
      if (desired == CURL_POLL_REMOVE || !descriptor.is_open())
        return;

      if ((desired & CURL_POLL_IN) && !read_pending) {
        read_pending = true;
        const std::uint64_t current = generation;
        auto self = shared_from_this();
        descriptor.async_wait(asio::posix::stream_descriptor::wait_read,
                              [self, current](const error_code& ec) {
                                self->ready(CURL_CSELECT_IN, current, ec);
                              });
      }

      if ((desired & CURL_POLL_OUT) && !write_pending) {
        write_pending = true;
        const std::uint64_t current = generation;
        auto self = shared_from_this();
        descriptor.async_wait(asio::posix::stream_descriptor::wait_write,
                              [self, current](const error_code& ec) {
                                self->ready(CURL_CSELECT_OUT, current, ec);
                              });
      }
    }

    void ready(int mask, std::uint64_t current, const error_code& ec) {
      if (mask == CURL_CSELECT_IN)
        read_pending = false;
      else
        write_pending = false;

      if (current != generation || desired == CURL_POLL_REMOVE)
        return;
      if (ec == asio::error::operation_aborted)
        return;

      int action = mask;
      if (ec)
        action |= CURL_CSELECT_ERR;
      if (mask == CURL_CSELECT_IN)
        ++owner.outcome_.read_completions;

      owner.drive(fd, action);

      if (owner.mode_ == Mode::Rearm && current == generation &&
          desired != CURL_POLL_REMOVE && !owner.outcome_.completed)
        arm();
    }

    MultiClient& owner;
    curl_socket_t fd;
    asio::posix::stream_descriptor descriptor;
    int desired = CURL_POLL_REMOVE;
    std::uint64_t generation = 0;
    bool read_pending = false;
    bool write_pending = false;
  };

  static size_t write_callback(char* data, size_t size, size_t count,
                               void* userdata) {
    auto& self = *static_cast<MultiClient*>(userdata);
    const size_t bytes = size * count;
    self.outcome_.body.append(data, bytes);
    return bytes;
  }

  static int socket_callback(CURL*, curl_socket_t fd, int what, void* userdata,
                             void*) {
    return static_cast<MultiClient*>(userdata)->on_socket(fd, what);
  }

  static int timer_callback(CURLM*, long timeout_ms, void* userdata) {
    return static_cast<MultiClient*>(userdata)->on_timer(timeout_ms);
  }

  int on_socket(curl_socket_t fd, int what) {
    auto it = watches_.find(fd);
    if (what == CURL_POLL_REMOVE) {
      if (it != watches_.end()) {
        it->second->remove();
        watches_.erase(it);
      }
      return 0;
    }

    if (it == watches_.end()) {
      auto watch = std::make_shared<Watch>(*this, fd);
      it = watches_.emplace(fd, std::move(watch)).first;
    }
    it->second->update(what);
    return 0;
  }

  int on_timer(long timeout_ms) {
    error_code ignored;
    curl_timer_.cancel(ignored);
    ++timer_generation_;
    if (timeout_ms < 0)
      return 0;

    const std::uint64_t current = timer_generation_;
    curl_timer_.expires_after(std::chrono::milliseconds(timeout_ms));
    curl_timer_.async_wait([this, current](const error_code& ec) {
      if (!ec && current == timer_generation_ && !outcome_.completed)
        drive(CURL_SOCKET_TIMEOUT, 0);
    });
    return 0;
  }

  void drive(curl_socket_t fd, int action) {
    int running = 0;
    CURLMcode code;
    do {
      code = curl_multi_socket_action(multi_, fd, action, &running);
    } while (code == CURLM_CALL_MULTI_PERFORM);
    check_multi(code);

    int remaining = 0;
    while (CURLMsg* message = curl_multi_info_read(multi_, &remaining)) {
      if (message->msg == CURLMSG_DONE && message->easy_handle == easy_) {
        outcome_.completed = true;
        outcome_.result = message->data.result;
        error_code ignored;
        deadline_.cancel(ignored);
        curl_timer_.cancel(ignored);
        io_.stop();
        return;
      }
    }
  }

  void cleanup() noexcept {
    if (cleaned_)
      return;
    cleaned_ = true;

    error_code ignored;
    deadline_.cancel(ignored);
    curl_timer_.cancel(ignored);

    if (added_ && multi_ && easy_) {
      curl_multi_remove_handle(multi_, easy_);
      added_ = false;
    }
    for (auto& [fd, watch] : watches_) {
      (void)fd;
      watch->remove();
    }
    watches_.clear();

    if (easy_) {
      curl_easy_cleanup(easy_);
      easy_ = nullptr;
    }
    if (multi_) {
      curl_multi_cleanup(multi_);
      multi_ = nullptr;
    }
  }

  static void check_easy(CURLcode code) {
    if (code != CURLE_OK)
      throw std::runtime_error(std::string("curl easy error: ") +
                               curl_easy_strerror(code));
  }

  static void check_multi(CURLMcode code) {
    if (code != CURLM_OK)
      throw std::runtime_error(std::string("curl multi error: ") +
                               curl_multi_strerror(code));
  }

  Mode mode_;
  asio::io_context io_;
  CURLM* multi_ = nullptr;
  CURL* easy_ = nullptr;
  asio::steady_timer curl_timer_;
  asio::steady_timer deadline_;
  std::map<curl_socket_t, std::shared_ptr<Watch>> watches_;
  std::uint64_t timer_generation_ = 0;
  bool added_ = false;
  bool cleaned_ = false;
  Outcome outcome_;
};

static MultiClient::Outcome run_case(MultiClient::Mode mode) {
  SplitServer server;
  const std::string url =
      "http://127.0.0.1:" + std::to_string(server.port()) + "/";
  MultiClient client(mode);
  return client.run(url,
                    mode == MultiClient::Mode::OneShot ? 1200ms : 2500ms);
}

int main() {
  const CURLcode global = curl_global_init(CURL_GLOBAL_ALL);
  if (global != CURLE_OK) {
    std::cerr << "curl_global_init: " << curl_easy_strerror(global) << '\n';
    return 2;
  }

  int exit_code = 0;
  try {
    const auto one_shot = run_case(MultiClient::Mode::OneShot);
    std::cout << "one-shot: completed=" << one_shot.completed
              << " timed_out=" << one_shot.timed_out
              << " reads=" << one_shot.read_completions << " body='"
              << one_shot.body << "'\n";

    const auto rearm = run_case(MultiClient::Mode::Rearm);
    std::cout << "rearm: completed=" << rearm.completed
              << " timed_out=" << rearm.timed_out
              << " reads=" << rearm.read_completions
              << " result=" << curl_easy_strerror(rearm.result) << " body='"
              << rearm.body << "'\n";

    const bool one_shot_proved =
        !one_shot.completed && one_shot.timed_out && one_shot.body == "hello ";
    const bool rearm_proved =
        rearm.completed && !rearm.timed_out && rearm.result == CURLE_OK &&
        rearm.body == "hello world!" && rearm.read_completions >= 2;

    if (!one_shot_proved || !rearm_proved) {
      std::cerr << "discriminator failed: one_shot=" << one_shot_proved
                << " rearm=" << rearm_proved << '\n';
      exit_code = 1;
    } else {
      std::cout << "curl multi-socket Asio re-arm discriminator: PASS\n";
    }
  } catch (const std::exception& e) {
    std::cerr << "fixture: " << e.what() << '\n';
    exit_code = 2;
  }

  curl_global_cleanup();
  return exit_code;
}
