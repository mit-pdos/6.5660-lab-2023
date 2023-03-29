/* dispatch daemon */

#include "http.h"
#include <err.h>
#include <regex.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <netdb.h>
#include <fcntl.h>
#include <sys/wait.h>
#include <sys/param.h>
#include <sys/types.h>
#include <sys/socket.h>

static void process_client(int);
static int run_server(const char *portstr);
static int start_server(const char *portstr);

int main(int argc, char **argv)
{
    if (argc != 2)
        errx(1, "Wrong arguments");

    run_server(argv[1]);
}

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

static void sigchld(int sig, siginfo_t *si, void *context)
{
    if (si->si_signo == SIGCHLD && WIFSIGNALED(si->si_status)) {
        printf("Child process %d terminated incorrectly, receiving signal %d\n",
               si->si_pid, WTERMSIG(si->si_status));
    }
}

static int run_server(const char *port)
{
    signal(SIGPIPE, SIG_IGN);

    struct sigaction sigchld_sa;
    memset(&sigchld_sa, 0, sizeof(sigchld_sa));
    sigchld_sa.sa_flags = SA_SIGINFO | SA_RESTART;
    sigchld_sa.sa_sigaction = sigchld;
    sigaction(SIGCHLD, &sigchld_sa, NULL);

    int sockfd = start_server(port);
    for (;;) {
        int cltfd = accept(sockfd, NULL, NULL);
        int pid;

        if (cltfd < 0)
            err(1, "accept");

        /* fork a new process for each client process, because the process
         * builds up state specific for a client (e.g. cookie and other
         * enviroment variables that are set by request). We want to get rid off
         * that state when we have processed the request and start the next
         * request in a pristine state.
         */
        switch ((pid = fork()))
        {
        case -1:
            err(1, "fork");

        case 0:
            process_client(cltfd);
            exit(0);
            break;

        default:
            close(cltfd);
            break;
        }
    }
}

static void process_client(int fd)
{
    static char env[8192];  /* static variables are not on the stack */
    static size_t env_len = 8192;
    char reqpath[4096];
    const char *errmsg;

    /* get the request line */
    if ((errmsg = http_request_line(fd, reqpath, env, &env_len)))
        return http_err(fd, 500, "http_request_line: %s", errmsg);

    env_deserialize(env, sizeof(env));

    /* get all headers */
    if ((errmsg = http_request_headers(fd)))
      http_err(fd, 500, "http_request_headers: %s", errmsg);
    else
      http_serve(fd, getenv("REQUEST_URI"));

    close(fd);
}

void accidentally(void)
{
    __asm__("mov 16(%%rbp), %%rdi": : :"rdi");
}
