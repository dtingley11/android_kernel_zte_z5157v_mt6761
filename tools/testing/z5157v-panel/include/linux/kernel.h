/* Minimal userspace shim for compiling the actual LCM source in the test. */
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
typedef uint8_t u8;
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define pr_info(...) ((void)0)
#define pr_debug(...) ((void)0)
