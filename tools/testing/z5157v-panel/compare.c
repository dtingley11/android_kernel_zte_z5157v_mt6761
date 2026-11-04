// SPDX-License-Identifier: GPL-2.0-only
/* Compare the recovered driver against isolated stock ARM callbacks.
 * All hardware access and kernel helpers are replaced with test callbacks.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <errno.h>
#include <linux/kernel.h>

#include "../../../drivers/misc/mediatek/lcm/zte_mango_zhongguangdian_er68577_720p_5p45_boe/zte_mango_zhongguangdian_er68577_720p_5p45_boe.c"

#define IMAGE_BASE 0xc0008000u
#define MAP_BASE 0xc0000000u
#define MAP_SIZE 0x02000000u
#define STOCK_DRIVER 0xc15bd65cu
#define MAX_EVENTS 512

struct event {
	unsigned int kind, a, b, c, handle;
	unsigned char payload[128];
};
/* Bionic static ARM executables require a 32-byte-aligned TLS segment. */
static __thread volatile int tls_alignment __attribute__((aligned(32)));
static struct event events[MAX_EVENTS];
static unsigned int nr_events, shutdown_flag, bad_read;

static struct event *record(unsigned int kind, unsigned int a,
			    unsigned int b, unsigned int c)
{
	struct event *e;
	if (nr_events == MAX_EVENTS) {
		fputs("Trace overflow\n", stderr);
		exit(1);
	}
	e = &events[nr_events++];
	memset(e, 0, sizeof(*e));
	e->kind = kind; e->a = a; e->b = b; e->c = c;
	return e;
}
static void reset(unsigned int n) { record('R', n, 0, 0); }
static void delay_ms(unsigned int n) { record('M', n, 0, 0); }
static void delay_us(unsigned int n) { record('U', n, 0, 0); }
void tps65132b_set_vsp_vsn_gpio(u8 n) { record('B', n, 0, 0); }
void tps65132b_set_vsp_vsn_level(u8 n) { record('V', n, 0, 0); }
unsigned int primary_display_get_shutdown_suspend_flag(void)
{
	return shutdown_flag;
}
static void dcs(void *handle, unsigned int cmd, unsigned char n,
		unsigned char *payload, unsigned char force)
{
	struct event *e = record('D', cmd, n, force);
	if (n > sizeof(e->payload)) abort();
	e->handle = (unsigned int)(uintptr_t)handle;
	memcpy(e->payload, payload, n);
}
static void cmdq(unsigned int *words, unsigned int n, unsigned char force)
{
	struct event *e = record('Q', n, force, 0);
	if (n * sizeof(*words) > sizeof(e->payload)) abort();
	memcpy(e->payload, words, n * sizeof(*words));
}
static unsigned int read_dcs(unsigned char cmd, unsigned char *buf,
			     unsigned char n)
{
	record('I', cmd, n, 0);
	memset(buf, 0, n);
	if (cmd == 0x53 && n) buf[0] = bad_read ? 0xbe : 0x24;
	if (cmd == 0x2a && n == 4) {
		buf[0] = 0; buf[1] = 180; buf[2] = 2;
		buf[3] = bad_read ? 0 : 28;
	}
	return n;
}
static void zero(void *p, unsigned int n) { memset(p, 0, n); }
static int quiet_printk(const char *fmt, ...) { (void)fmt; return 0; }
static void stock_stack_fail(void) { fputs("Stock stack check failed\n", stderr); abort(); }

static void redirect(uintptr_t addr, void (*fn)(void))
{
	uint32_t *p = (uint32_t *)addr;
	p[0] = 0xe51ff004; /* ldr pc, [pc, #-4] */
	p[1] = (uint32_t)(uintptr_t)fn;
	__builtin___clear_cache((char *)p, (char *)(p + 2));
}

static void run(struct LCM_DRIVER *d, unsigned int op)
{
	unsigned char buf[4] = {0};
	void *mode;
	unsigned int ret;
	switch (op) {
	case 0: d->init_power(); break;
	case 1: d->init(); break;
	case 2: d->resume_power(); break;
	case 3: d->suspend(); break;
	case 4: shutdown_flag = 0; d->suspend_power(); break;
	case 5: shutdown_flag = 1; d->suspend_power(); break;
	case 6: d->resume(); break;
	case 7: record('C', d->compare_id(), 0, 0); break;
	case 8: bad_read = 0; record('E', d->esd_check(), 0, 0); break;
	case 9: bad_read = 1; record('E', d->esd_check(), 0, 0); break;
	case 10: bad_read = 0; ret = d->ata_check(buf); record('A', ret, 0, 0); break;
	case 11: bad_read = 1; ret = d->ata_check(buf); record('A', ret, 0, 0); break;
	case 12: d->update(3, 5, 200, 400); break;
	case 13: d->update(0, 0, 720, 1440); break;
	case 14: case 15:
		mode = d->switch_mode(op - 14);
		memcpy(record('S', 0, 0, 0)->payload, mode,
		       sizeof(struct LCM_DSI_MODE_SWITCH_CMD));
		break;
	default: d->set_backlight_cmdq((void *)0x1234, op - 16); break;
	}
}

int main(int argc, char **argv)
{
	FILE *fp;
	void *mapped;
	struct LCM_DRIVER *stock = (void *)STOCK_DRIVER;
	struct LCM_DRIVER *restored = &zte_mango_zhongguangdian_er68577_720p_5p45_boe_lcm_drv;
	struct LCM_UTIL_FUNCS util = {
		.set_reset_pin = reset, .mdelay = delay_ms, .udelay = delay_us,
		.dsi_set_cmdq_V22 = dcs, .dsi_set_cmdq = cmdq,
		.dsi_dcs_read_lcm_reg_v2 = read_dcs,
	};
	struct LCM_PARAMS original, recovered;
	struct event expected[MAX_EVENTS];
	unsigned int op, count, i;
	size_t loaded;
	tls_alignment = 1;
	if (argc != 2) return 2;
	mapped = mmap((void *)MAP_BASE, MAP_SIZE, PROT_READ | PROT_WRITE | PROT_EXEC,
		      MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
	if (mapped == MAP_FAILED) { perror("mmap stock image"); return 1; }
	fp = fopen(argv[1], "rb");
	if (!fp) { perror("stock image"); return 1; }
	loaded = fread((void *)IMAGE_BASE, 1, MAP_SIZE - (IMAGE_BASE - MAP_BASE), fp);
	if (ferror(fp) || !feof(fp)) return 1;
	fclose(fp);
	if (loaded != 23502848u || strcmp(stock->name, restored->name)) {
		fputs("Unexpected stock image or driver table\n", stderr); return 1;
	}
	redirect(0xc04de260u, (void (*)(void))zero);
	redirect(0xc04ddb00u, (void (*)(void))memcpy);
	redirect(0xc025ca60u, (void (*)(void))quiet_printk);
	redirect(0xc0126a20u, stock_stack_fail);
	redirect(0xc09281a0u, (void (*)(void))primary_display_get_shutdown_suspend_flag);
	redirect(0xc095f304u, (void (*)(void))tps65132b_set_vsp_vsn_gpio);
	redirect(0xc095f3acu, (void (*)(void))tps65132b_set_vsp_vsn_level);
	stock->set_util_funcs(&util); restored->set_util_funcs(&util);
	if (sizeof(util) != 124 || sizeof(original) != 1204) {
		fputs("LCM ABI mismatch\n", stderr); return 1;
	}
	memset(&original, 0xa5, sizeof(original));
	memset(&recovered, 0xa5, sizeof(recovered));
	stock->get_params(&original); restored->get_params(&recovered);
	if (memcmp(&original, &recovered, sizeof(original))) {
		for (i = 0; i < sizeof(original); i++)
			if (((unsigned char *)&original)[i] != ((unsigned char *)&recovered)[i])
				fprintf(stderr, "Parameter offset %u: stock=%02x recovered=%02x\n", i,
					((unsigned char *)&original)[i], ((unsigned char *)&recovered)[i]);
		return 1;
	}
	puts("PASS: all 1204 parameter bytes match the stock callback");
	for (op = 0; op < 16 + 257; op++) {
		nr_events = 0; run(stock, op); count = nr_events;
		memcpy(expected, events, count * sizeof(*events));
		nr_events = 0; run(restored, op);
		if (nr_events != count || memcmp(expected, events, count * sizeof(*events))) {
			fprintf(stderr, "Callback case %u mismatch: stock=%u restored=%u events\n",
				op, count, nr_events);
			for (i = 0; i < count && i < nr_events; i++)
				if (memcmp(&expected[i], &events[i], sizeof(*events)))
					fprintf(stderr, "Event %u: stock=%c/%u/%u restored=%c/%u/%u\n", i,
						expected[i].kind, expected[i].a, expected[i].b,
						events[i].kind, events[i].a, events[i].b);
			return 1;
		}
	}
	puts("PASS: 273 callback cases match stock command, reset, delay and power traces");
	puts("Hardware, bootloader selection, electrical timing and display operation remain untested");
	return 0;
}
