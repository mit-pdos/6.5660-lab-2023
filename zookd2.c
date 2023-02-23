/* dispatch daemon */

#include "http.h"
#include <err.h>
#include <regex.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define MAX_SERVICES 256
static int nsvcs;
static regex_t svcurls[MAX_SERVICES];
static char svchosts[MAX_SERVICES][1024];
static int svcports[MAX_SERVICES];

static void process_client(int);
static int start_daemon(int fd, int sockfd);

int main(int argc, char **argv)
{
    if (argc != 3)
        errx(1, "Wrong arguments");
    start_daemon(atoi(argv[1]), atoi(argv[2]));
}

static int start_daemon(int fd, int sockfd)
{
    int i;

    signal(SIGPIPE, SIG_IGN);
    signal(SIGCHLD, SIG_IGN);

    /* receive the number of services and the server socket from zookld */
    if (read(fd, &nsvcs, sizeof(nsvcs)) != sizeof(nsvcs))
        err(1, "read nsvcs");
    warnx("Start with %d service(s)", nsvcs);

    /* receive url patterns of all services */
    for (i = 0; i != nsvcs; ++i)
    {
        char url[1024], regexp[1028];
        memset(url, '\0', sizeof(url));
        int len = 0;
        int n;
        if ((n = read(fd, &len, sizeof(len))) != sizeof(len))
            err(1, "recv urllen %d %d", i, n);
        if (read(fd, url, len) != len)
            err(1, "recv url %d", i);
       /* parens are necessary here so that regexes like a|b get
          parsed properly and not as (^a)|(b$) */
        snprintf(regexp, sizeof(regexp), "^(%s)$", url);
        if (regcomp(&svcurls[i], regexp, REG_EXTENDED | REG_NOSUB))
            errx(1, "Bad url for service %d: %s", i, url);
        warnx("Dispatch %s for service %d", regexp, i);
    }

    /* receive hosts of all services */
    for (i = 0; i != nsvcs; ++i) {
        int link = 0;
        if (read(fd, &link, sizeof(link)) != sizeof(link))
            err(1, "recv link %d failed", i);
        snprintf(svchosts[i], sizeof(svchosts[i]), "10.1.%d.4", link);
        warnx("Host %s (link %d) service %d", svchosts[i], link, i);
    }

    /* receive ports of all services */
    for (i = 0; i != nsvcs; ++i) {
        if (read(fd, &(svcports[i]), sizeof(svcports[i])) != sizeof(svcports[i]))
            err(1, "recv port %d failed", i);
        warnx("Port %d for service %d", svcports[i], i);
    }

    close(fd);

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

int read_line(int fd, char *buf, size_t size, int eoh)
{
    size_t i = 0;
    for (;;) {
        int cc = read(fd, &buf[i], 1);
        if (cc < 0)
            break;

        if (cc == 0)
            return 0;

        if (eoh && i == 1 && buf[0] == '\r' && buf[1] == '\n') {
            return 0;
        }

        if (buf[i] == '\n') {
            return i+1;
        }

        if (i >= size - 1) {
            buf[i] = '\0';
            return i+1;
        }
        i++;
    }
    return -1;
}

static int proxy(int i, int fd, char *env, size_t env_len)
{
    static char buf[8192];  /* static variables are not on the stack */
    static char buf1[8192];  /* static variables are not on the stack */
    int sockfd, portno;
    struct sockaddr_in servaddr;
    char *server;
    int n;
    const char *r;
    char value[512];
    char envvar[512];
    int len = 0;

    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0)
        warn("cannot open socket");

    server = &(svchosts[i][0]);
    portno = svcports[i];

    bzero((char *) &servaddr, sizeof(servaddr));
    servaddr.sin_family = AF_INET;
    servaddr.sin_addr.s_addr = inet_addr(server);
    servaddr.sin_port = htons(portno);
    if (connect(sockfd, (struct sockaddr *) &servaddr, sizeof(servaddr)) < 0) {
        warn("connect failure to svc %d", i);
        return -1;
    }

    if (write(sockfd, &env_len, sizeof(env_len)) < 0) {
        warn("write to svc %d failed", i);
    }

    if (write(sockfd, env, env_len) < 0) {
        warn("write to svc %d failed", i);
    }

    // proxy header
    while(1) {
        memset(buf, '\0', sizeof(buf));
        if ((n = read_line(fd, buf, sizeof(buf), 1)) < 0) {
            warn("read_line from client failed");
            return -1;
        }

        if (n == 0) {
            write(sockfd, buf, 2);
            break;
        }

        memcpy(buf1, buf, sizeof(buf));

        if ((r = http_parse_line(buf1, envvar, value)) != NULL) {
            warn("parse_line: invalid");
            return -1;
        }

        if (strcmp(envvar, "CONTENT_LENGTH") == 0) {
            len = atoi(value);
        }

        if (write(sockfd, buf, n) != n) {
            warn("write to svc failed");
            return -1;
        }
    }

    // proxy body
    while (len > 0) {
        if ((n = read(fd, buf, sizeof(buf))) < 0) {
            warn("read from svc failed");
            return -1;
        }
        if (write(sockfd, buf, n) != n) {
            warn("write body to client failed");
            return -1;
        }
        len -= n;
    }

    // proxy response
    while (1) {
        memset(buf, '\0', sizeof(buf));
        if ((n = read(sockfd, buf, sizeof(buf))) < 0) {
            warn("read from svc failed");
            return -1;
        }
        if (n == 0) {
            break;
        }
        if (write(fd, buf, n) != n) {
            warn("write body to client failed");
            return -1;
        }
    }

    return 0;
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

    int i;
    for (i = 0; i < nsvcs; i++) {
        if (!regexec(&svcurls[i], reqpath, 0, 0, 0)) {
            warnx("Forwarding to %s:%d for %s", svchosts[i], svcports[i], reqpath);
            break;
        }
    }

    if (i == nsvcs)
        return http_err(fd, 500, "Error dispatching request: %s", reqpath);

    if (proxy(i, fd, env, env_len) < 0)
        return http_err(fd, 500, "Error proxying request: %s", reqpath);

    close(fd);
}
