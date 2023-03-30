#pragma once

#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <stddef.h>

/** Read the request line like "GET /xxx HTTP/1.0".
 *  \return Error message, or NULL if succeed.
 */
const char *http_request_line(int fd, char *reqpath, char *env, size_t *env_len);

/** Parse HTTP header line.  Parsing modifies buf content.
 *  \return Error message, or NULL if succeed.
 */
const char *http_parse_line(char *buf, char *envvar, char *value);

/** Read all HTTP request headers.
 *  \return Error message, or NULL if succeed.
 */
const char *http_request_headers(int fd);

/** Send an HTTP error message. */
void http_err(int fd, int code, char *fmt, ...);

/** Dispatcher for generating an HTTP response. */
void http_serve(int fd, const char *);

void http_serve_none(int fd, const char *);

void http_serve_file(int fd, const char *);

void http_serve_directory(int fd, const char *);

void http_serve_executable(int fd, const char *);

/** URL decoder. */
void url_decode(char *dst, const char *src);

/** Unpack and set environmental strings. */
void env_deserialize(const char *env, size_t len);

void fdprintf(int fd, char *fmt, ...);
