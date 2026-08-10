#include <boost/asio.hpp>

#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cstdlib>
#include <iostream>

struct Result {
  int actions = 0;
  bool stale_suppressed = false;
  bool aborted = false;
  bool fd_valid = false;
};

Result run_case(bool generation_safe)
{
  namespace asio = boost::asio;
  using stream_socket = asio::generic::stream_protocol::socket;

  asio::io_context io;
  int first_pair[2];
  if (::socketpair(AF_UNIX, SOCK_STREAM, 0, first_pair) != 0) {
    std::abort();
  }

  const int fd = first_pair[0];
  stream_socket socket(io);
  boost::system::error_code ec;
  socket.assign(asio::generic::stream_protocol(AF_UNIX, 0), fd, ec);
  if (ec) {
    std::abort();
  }

  unsigned current_generation = 1;
  const unsigned wait_generation = current_generation;
  Result result;

  socket.async_wait(stream_socket::wait_read,
                    [&, wait_generation](boost::system::error_code wait_ec) {
    if (generation_safe && wait_generation != current_generation) {
      result.stale_suppressed = true;
      return;
    }

    ++result.actions;
    result.aborted = (wait_ec == asio::error::operation_aborted);
    result.fd_valid = (::fcntl(fd, F_GETFD) != -1);
  });

  // Model CURL_POLL_REMOVE invalidating all waits from the old watch.
  ++current_generation;

  const int released_fd = socket.release(ec);
  if (ec) {
    std::abort();
  }
  ::close(released_fd);
  ::close(first_pair[1]);

  int second_pair[2];
  if (::socketpair(AF_UNIX, SOCK_STREAM, 0, second_pair) != 0) {
    std::abort();
  }

  if (second_pair[0] != fd) {
    if (::dup2(second_pair[0], fd) < 0) {
      std::abort();
    }
    ::close(second_pair[0]);
    second_pair[0] = fd;
  }

  const char byte = 'X';
  if (::write(second_pair[1], &byte, 1) != 1) {
    std::abort();
  }

  io.run();

  ::close(second_pair[0]);
  ::close(second_pair[1]);
  return result;
}

int main()
{
  const Result broken = run_case(false);
  const Result safe = run_case(true);

  std::cout << "broken: actions=" << broken.actions
            << " aborted=" << broken.aborted
            << " fd_valid=" << broken.fd_valid
            << " stale_suppressed=" << broken.stale_suppressed << '\n';
  std::cout << "generation-safe: actions=" << safe.actions
            << " aborted=" << safe.aborted
            << " fd_valid=" << safe.fd_valid
            << " stale_suppressed=" << safe.stale_suppressed << '\n';

  const bool passed = broken.actions == 1 &&
      broken.aborted &&
      broken.fd_valid &&
      safe.actions == 0 &&
      safe.stale_suppressed;

  std::cout << "stale-generation discriminator: "
            << (passed ? "PASS" : "FAIL") << '\n';
  return passed ? 0 : 1;
}
