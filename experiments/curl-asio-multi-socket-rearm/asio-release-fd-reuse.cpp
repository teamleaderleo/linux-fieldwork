#include <boost/asio.hpp>
#include <boost/system/error_code.hpp>

#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <iostream>

int main()
{
  namespace asio = boost::asio;
  using stream_socket = asio::generic::stream_protocol::socket;

  asio::io_context io;

  int first_pair[2];
  if (::socketpair(AF_UNIX, SOCK_STREAM, 0, first_pair) != 0) {
    perror("socketpair(first)");
    return 2;
  }

  const int watched_fd = first_pair[0];
  stream_socket socket(io);
  boost::system::error_code ec;
  socket.assign(asio::generic::stream_protocol(AF_UNIX, 0), watched_fd, ec);
  if (ec) {
    std::cerr << "assign: " << ec.message() << '\n';
    return 3;
  }

  bool callback_ran = false;
  boost::system::error_code callback_ec;
  bool fd_valid_in_callback = false;

  socket.async_wait(stream_socket::wait_read,
                    [&](boost::system::error_code wait_ec) {
    callback_ran = true;
    callback_ec = wait_ec;
    fd_valid_in_callback = (::fcntl(watched_fd, F_GETFD) != -1);

    std::cout << "callback ec=" << wait_ec.value()
              << " ('" << wait_ec.message() << "')"
              << " fd=" << watched_fd
              << " fd_valid_now=" << fd_valid_in_callback << '\n';
  });

  const int released_fd = socket.release(ec);
  if (ec) {
    std::cerr << "release: " << ec.message() << '\n';
    return 4;
  }

  std::cout << "released=" << released_fd
            << " watched_fd=" << watched_fd << '\n';

  ::close(released_fd);
  ::close(first_pair[1]);

  int second_pair[2];
  if (::socketpair(AF_UNIX, SOCK_STREAM, 0, second_pair) != 0) {
    perror("socketpair(second)");
    return 5;
  }

  std::cout << "new pair before force=" << second_pair[0]
            << ',' << second_pair[1] << '\n';

  if (second_pair[0] != watched_fd) {
    if (::dup2(second_pair[0], watched_fd) < 0) {
      perror("dup2");
      return 6;
    }
    ::close(second_pair[0]);
    second_pair[0] = watched_fd;
  }

  const char byte = 'X';
  if (::write(second_pair[1], &byte, 1) != 1) {
    perror("write");
    return 7;
  }

  std::cout << "new unrelated socket now occupies fd="
            << second_pair[0] << '\n';

  io.run();

  const bool passed = callback_ran &&
      callback_ec == asio::error::operation_aborted &&
      fd_valid_in_callback;

  std::cout << "summary callback=" << callback_ran
            << " operation_aborted="
            << (callback_ec == asio::error::operation_aborted)
            << " fd_reused_and_valid=" << fd_valid_in_callback << '\n';

  ::close(second_pair[0]);
  ::close(second_pair[1]);
  return passed ? 0 : 1;
}
