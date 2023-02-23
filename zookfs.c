/* file server */

#include "http.h"
#include <stdio.h>
#include <err.h>
#include <signal.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <netdb.h>

/* socket-bind-listen idiom */
static int start_server(const char *portstr)
{
    struct addrinfo hints = {0}, *res;
    int sockfd;
    int e, opt = 1;

    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;

    if ((e = getaddrinfo(NULL, portstr, &hints, &res)))
        errx(1, "getaddrinfo: %s", gai_strerror(e));
    if ((sockfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol)) < 0)
        err(1, "socket");
    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)))
        err(1, "setsockopt");

    if (fcntl(sockfd, F_SETFD, FD_CLOEXEC) < 0)
        err(1, "fcntl");
    if (bind(sockfd, res->ai_addr, res->ai_addrlen))
        err(1, "bind");
    if (listen(sockfd, 5))
        err(1, "listen");
    freeaddrinfo(res);
    unlink("/tmp/zook-start-wait");

    return sockfd;
}

static void process_client(int fd)
{
  char envp[8192];
  size_t env_len;

  const char *errmsg;

  if ((read(fd, &env_len, sizeof(env_len)) < 0))
    err(1, "read");

  if ((read(fd, envp, env_len) != env_len))
    err(1, "read");

  /* set envp */
  env_deserialize(envp, sizeof(envp));
  /* get all headers */

  if ((errmsg = http_request_headers(fd)))
    http_err(fd, 500, "http_request_headers: %s", errmsg);
  else
    http_serve(fd, getenv("REQUEST_URI"));
}

int main(int argc, char **argv)
{
    int sockfd;
    if (argc != 2)
        errx(1, "Wrong arguments");

    signal(SIGPIPE, SIG_IGN);
    signal(SIGCHLD, SIG_IGN);

    sockfd = start_server(argv[1]);

    // Make sure there are no buffered writes before forking
    fflush(stdout);
    fflush(stderr);

    for (;;)
    {
        int cltfd = accept(sockfd, NULL, NULL);
        if (cltfd < 0)
            err(1, "accept");
        switch (fork())
        {
        case -1: /* error */
            err(1, "fork");
        case 0:  /* child */
            process_client(cltfd);
            return 0;
        default: /* parent */
            close(cltfd);
            break;
        }
    }
}
