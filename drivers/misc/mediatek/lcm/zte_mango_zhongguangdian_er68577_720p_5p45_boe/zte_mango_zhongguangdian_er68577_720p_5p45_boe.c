/*
 * Copyright (C) 2015 MediaTek Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 */

/* Recovered from the Z5157V stock 20210805_v0 panel implementation.
 * See Documentation/display/z5157v-er68577.md for provenance and validation.
 */
#include <linux/kernel.h>
#include <linux/string.h>
#include "lcm_drv.h"

#define LCM_LOGI(fmt, args...) pr_info("[KERNEL/LCM]" fmt, ##args)
#define FRAME_WIDTH 720
#define FRAME_HEIGHT 1440
#define LCM_PHYSICAL_WIDTH 61884
#define LCM_PHYSICAL_HEIGHT 123768
#define LCM_DENSITY 320
#define REGFLAG_DELAY 0xfffc
#define REGFLAG_UDELAY 0xfffb
#define REGFLAG_END_OF_TABLE 0xfffd
#define TRUE 1
#define FALSE 0

static struct LCM_UTIL_FUNCS lcm_util;
static struct LCM_DSI_MODE_SWITCH_CMD lcm_switch_mode_cmd;

#define SET_RESET_PIN(v) (lcm_util.set_reset_pin(v))
#define MDELAY(n) (lcm_util.mdelay(n))
#define UDELAY(n) (lcm_util.udelay(n))
#define dsi_set_cmdq_V22(q, cmd, count, para, force) \
	lcm_util.dsi_set_cmdq_V22(q, cmd, count, para, force)
#define dsi_set_cmdq(data, count, force) \
	lcm_util.dsi_set_cmdq(data, count, force)
#define read_reg_v2(cmd, buffer, count) \
	lcm_util.dsi_dcs_read_lcm_reg_v2(cmd, buffer, count)

struct LCM_setting_table {
	unsigned int cmd;
	unsigned char count;
	unsigned char para_list[64];
};

static struct LCM_setting_table lcm_suspend_setting[] = {
	{0x28, 0, {} },
	{REGFLAG_DELAY, 50, {} },
	{0x10, 0, {} },
	{REGFLAG_DELAY, 240, {} },
	{0xe9, 1, {0xc1} },
	{0xc6, 6, {0x01, 0x00, 0xff, 0xff, 0x00, 0xff} },
};

static struct LCM_setting_table init_setting[] = {
	{0xe0, 2, {0xab, 0xba} },
	{0xe1, 2, {0xba, 0xab} },
	{0xb1, 4, {0x10, 0x01, 0x47, 0xff} },
	{0xb2, 6, {0x0c, 0x14, 0x04, 0x50, 0x50, 0x14} },
	{0xb3, 3, {0x56, 0x52, 0xa0} },
	{0xb4, 3, {0x2a, 0x30, 0x04} },
	{0xb6, 7, {0x00, 0x00, 0x00, 0x10, 0x00, 0x10, 0x00} },
	{0xb8, 7, {0x05, 0x12, 0x29, 0x49, 0x48, 0x00, 0x00} },
	{0xb9, 38, {0x7c, 0x6d, 0x64, 0x5b, 0x5c, 0x4f, 0x54, 0x3e, 0x56, 0x54, 0x4f, 0x68, 0x51, 0x59, 0x48, 0x44, 0x37, 0x26, 0x06, 0x7c, 0x6d, 0x64, 0x5b, 0x5c, 0x4f, 0x54, 0x3e, 0x56, 0x54, 0x4f, 0x68, 0x51, 0x59, 0x48, 0x44, 0x37, 0x26, 0x06} },
	{0xc0, 16, {0x76, 0x54, 0x12, 0x34, 0x44, 0x44, 0x44, 0x44, 0x90, 0x04, 0x80, 0x04, 0x0f, 0x00, 0x00, 0xc1} },
	{0xc1, 10, {0x54, 0x94, 0x02, 0x85, 0x90, 0x04, 0x80, 0x04, 0x54, 0x00} },
	{0xc2, 12, {0x37, 0x09, 0x08, 0x89, 0x08, 0x11, 0x22, 0x33, 0x44, 0x82, 0x18, 0x00} },
	{0xc3, 22, {0xa3, 0x40, 0x06, 0x04, 0x10, 0x12, 0x0c, 0x0e, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x00, 0x00, 0x00, 0x22, 0x01} },
	{0xc4, 22, {0x23, 0x00, 0x07, 0x05, 0x11, 0x13, 0x0d, 0x0f, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x00, 0x00, 0x00, 0x22, 0x01} },
	{0xc8, 6, {0x21, 0x00, 0x31, 0x55, 0x34, 0x16} },
	{0xc9, 5, {0xa1, 0x22, 0xff, 0x00, 0x23} },
	{0xca, 2, {0xb2, 0x43} },
	{0xcd, 8, {0x0e, 0x64, 0x64, 0x11, 0x1e, 0x6b, 0x06, 0xb3} },
	{0xd2, 4, {0xe2, 0x2b, 0x38, 0x00} },
	{0xd4, 11, {0x00, 0x01, 0x00, 0x0e, 0x04, 0x44, 0x08, 0x10, 0x00, 0x00, 0x00} },
	{0xe6, 8, {0x80, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff} },
	{0xf0, 5, {0x52, 0xf9, 0x21, 0x00, 0xff} },
	{0xf3, 1, {0x00} },
	{0x35, 1, {0x00} },
	{0x51, 1, {0x00} },
	{0x53, 1, {0x2c} },
	{0x55, 1, {0x00} },
	{0x5e, 1, {0x04} },
	{0x11, 1, {0x00} },
	{REGFLAG_DELAY, 120, {} },
	{0x29, 1, {0x00} },
	{REGFLAG_DELAY, 20, {} },
};

static struct LCM_setting_table bl_level[] = {
	{0x51, 1, {0xff} },
	{REGFLAG_END_OF_TABLE, 0, {} },
};

static void push_table(void *cmdq, struct LCM_setting_table *table,
	unsigned int count, unsigned char force_update)
{
	unsigned int i;
	unsigned int cmd;

	for (i = 0; i < count; i++) {
		cmd = table[i].cmd;

		switch (cmd) {

		case REGFLAG_DELAY:
			if (table[i].count <= 10)
				MDELAY(table[i].count);
			else
				MDELAY(table[i].count);
			break;

		case REGFLAG_UDELAY:
			UDELAY(table[i].count);
			break;

		case REGFLAG_END_OF_TABLE:
			break;

		default:
			dsi_set_cmdq_V22(cmdq, cmd, table[i].count, table[i].para_list, force_update);
		}
	}
}


static void lcm_set_util_funcs(const struct LCM_UTIL_FUNCS *util)
{
	memcpy(&lcm_util, util, sizeof(struct LCM_UTIL_FUNCS));
}


static void lcm_get_params(struct LCM_PARAMS *params)
{
	memset(params, 0, sizeof(*params));
	params->type = LCM_TYPE_DSI;
	params->width = FRAME_WIDTH;
	params->height = FRAME_HEIGHT;
	params->physical_width = LCM_PHYSICAL_WIDTH / 1000;
	params->physical_height = LCM_PHYSICAL_HEIGHT / 1000;
	params->physical_width_um = LCM_PHYSICAL_WIDTH;
	params->physical_height_um = LCM_PHYSICAL_HEIGHT;
	params->density = LCM_DENSITY;
	params->dbi.te_mode = LCM_DBI_TE_MODE_VSYNC_ONLY;
	params->dbi.te_edge_polarity = LCM_POLARITY_RISING;
	params->dsi.mode = SYNC_PULSE_VDO_MODE;
	params->dsi.switch_mode_enable = 0;
	params->dsi.LANE_NUM = LCM_THREE_LANE;
	params->dsi.data_format.color_order = LCM_COLOR_ORDER_RGB;
	params->dsi.data_format.trans_seq = LCM_DSI_TRANS_SEQ_MSB_FIRST;
	params->dsi.data_format.padding = LCM_DSI_PADDING_ON_LSB;
	params->dsi.data_format.format = LCM_DSI_FORMAT_RGB888;
	params->dsi.packet_size = 256;
	params->dsi.intermediat_buffer_num = 2;
	params->dsi.PS = LCM_PACKED_PS_24BIT_RGB888;
	params->dsi.vertical_sync_active = 4;
	params->dsi.vertical_backporch = 30;
	params->dsi.vertical_frontporch = 20;
	params->dsi.vertical_frontporch_for_low_power = 540;
	params->dsi.vertical_active_line = FRAME_HEIGHT;
	params->dsi.horizontal_sync_active = 40;
	params->dsi.horizontal_backporch = 72;
	params->dsi.horizontal_frontporch = 80;
	params->dsi.horizontal_active_pixel = FRAME_WIDTH;
	params->dsi.PLL_CLOCK = 343;
	params->dsi.PLL_CK_CMD = 240;
	params->dsi.PLL_CK_VDO = 343;
	params->dsi.CLK_HS_POST = 36;
	params->dsi.HS_PRPR = 5;
	params->dsi.ssc_disable = 1;
	params->dsi.clk_lp_per_line_enable = 0;
	params->dsi.esd_check_enable = 1;
	params->dsi.customization_esd_check_enable = 1;
	params->dsi.lcm_esd_check_table[0].cmd = 0x0a;
	params->dsi.lcm_esd_check_table[0].count = 1;
	params->dsi.lcm_esd_check_table[0].para_list[0] = 0x1c;
	params->dsi.lcm_backlight_curve_mode = 350;
}

extern unsigned int primary_display_get_shutdown_suspend_flag(void);
#ifdef CONFIG_ZTE_LCDBL_I2C_CTRL_VSP_VSN
extern void tps65132b_set_vsp_vsn_gpio(u8 enable);
extern void tps65132b_set_vsp_vsn_level(u8 level);
#endif

static void lcm_init_power(void)
{
}

static void lcm_suspend_power(void)
{
	unsigned int shutdown = primary_display_get_shutdown_suspend_flag();

	MDELAY(shutdown == 1 ? 20 : 10);
	SET_RESET_PIN(0);
	MDELAY(shutdown == 1 ? 120 : 10);
#ifdef CONFIG_ZTE_LCDBL_I2C_CTRL_VSP_VSN
	tps65132b_set_vsp_vsn_gpio(0);
#endif
}

static void lcm_resume_power(void)
{
	SET_RESET_PIN(0);
	MDELAY(10);
	SET_RESET_PIN(1);
	MDELAY(10);
}

static void lcm_init(void)
{
#ifdef CONFIG_ZTE_LCDBL_I2C_CTRL_VSP_VSN
	tps65132b_set_vsp_vsn_gpio(1);
	tps65132b_set_vsp_vsn_level(0x10);
#endif
	SET_RESET_PIN(0);
	MDELAY(1);
	SET_RESET_PIN(1);
	MDELAY(80);
	push_table(NULL, init_setting, ARRAY_SIZE(init_setting), 1);
}

static void lcm_suspend(void)
{
	push_table(NULL, lcm_suspend_setting,
		   ARRAY_SIZE(lcm_suspend_setting), 1);
}

static void lcm_resume(void)
{
	LCM_LOGI("%s: kernel----zte_mango_zhongguangdian_er68577_720p_5p45_boe 20210805_v0----\n", __func__);
	lcm_init();
}

static void lcm_update(unsigned int x, unsigned int y, unsigned int width, unsigned int height)
{
	unsigned int x0 = x;
	unsigned int y0 = y;
	unsigned int x1 = x0 + width - 1;
	unsigned int y1 = y0 + height - 1;

	unsigned char x0_MSB = ((x0 >> 8) & 0xFF);
	unsigned char x0_LSB = (x0 & 0xFF);
	unsigned char x1_MSB = ((x1 >> 8) & 0xFF);
	unsigned char x1_LSB = (x1 & 0xFF);
	unsigned char y0_MSB = ((y0 >> 8) & 0xFF);
	unsigned char y0_LSB = (y0 & 0xFF);
	unsigned char y1_MSB = ((y1 >> 8) & 0xFF);
	unsigned char y1_LSB = (y1 & 0xFF);

	unsigned int data_array[16];

	data_array[0] = 0x00053902;
	data_array[1] = (x1_MSB << 24) | (x0_LSB << 16) | (x0_MSB << 8) | 0x2a;
	data_array[2] = (x1_LSB);
	dsi_set_cmdq(data_array, 3, 1);

	data_array[0] = 0x00053902;
	data_array[1] = (y1_MSB << 24) | (y0_LSB << 16) | (y0_MSB << 8) | 0x2b;
	data_array[2] = (y1_LSB);
	dsi_set_cmdq(data_array, 3, 1);

	data_array[0] = 0x002c3909;
	dsi_set_cmdq(data_array, 1, 0);
}

static unsigned int lcm_compare_id(void)
{
	return 1;
}


/* return TRUE: need recovery */
/* return FALSE: No need recovery */
static unsigned int lcm_esd_check(void)
{
#ifndef BUILD_LK
	unsigned char buffer[3];
	unsigned int array[4];

	array[0] = 0x00013700;
	dsi_set_cmdq(array, 1, 1);

	read_reg_v2(0x53, buffer, 1);

	if (buffer[0] != 0x24) {
		LCM_LOGI("[LCM ERROR] [0x53]=0x%02x\n", buffer[0]);
		return TRUE;
	}
	LCM_LOGI("[LCM NORMAL] [0x53]=0x%02x\n", buffer[0]);
	return FALSE;
#else
	return FALSE;
#endif

}

static unsigned int lcm_ata_check(unsigned char *buffer)
{
#ifndef BUILD_LK
	unsigned int ret = 0;
	unsigned int x0 = FRAME_WIDTH / 4;
	unsigned int x1 = FRAME_WIDTH * 3 / 4;

	unsigned char x0_MSB = ((x0 >> 8) & 0xFF);
	unsigned char x0_LSB = (x0 & 0xFF);
	unsigned char x1_MSB = ((x1 >> 8) & 0xFF);
	unsigned char x1_LSB = (x1 & 0xFF);

	unsigned int data_array[3];
	unsigned char read_buf[4];

	LCM_LOGI("ATA check size = 0x%x,0x%x,0x%x,0x%x\n", x0_MSB, x0_LSB, x1_MSB, x1_LSB);
	data_array[0] = 0x0005390A;	/* HS packet */
	data_array[1] = (x1_MSB << 24) | (x0_LSB << 16) | (x0_MSB << 8) | 0x2a;
	data_array[2] = (x1_LSB);
	dsi_set_cmdq(data_array, 3, 1);

	data_array[0] = 0x00043700;	/* read id return two byte,version and id */
	dsi_set_cmdq(data_array, 1, 1);

	read_reg_v2(0x2A, read_buf, 4);

	if ((read_buf[0] == x0_MSB) && (read_buf[1] == x0_LSB)
	    && (read_buf[2] == x1_MSB) && (read_buf[3] == x1_LSB))
		ret = 1;
	else
		ret = 0;

	x0 = 0;
	x1 = FRAME_WIDTH - 1;

	x0_MSB = ((x0 >> 8) & 0xFF);
	x0_LSB = (x0 & 0xFF);
	x1_MSB = ((x1 >> 8) & 0xFF);
	x1_LSB = (x1 & 0xFF);

	data_array[0] = 0x0005390A;	/* HS packet */
	data_array[1] = (x1_MSB << 24) | (x0_LSB << 16) | (x0_MSB << 8) | 0x2a;
	data_array[2] = (x1_LSB);
	dsi_set_cmdq(data_array, 3, 1);
	return ret;
#else
	return 0;
#endif
}

static void lcm_setbacklight_cmdq(void *handle, unsigned int level)
{

	LCM_LOGI("%s,backlight: level = %d\n", __func__, level);

	bl_level[0].para_list[0] = level;

	push_table(handle, bl_level, sizeof(bl_level) / sizeof(struct LCM_setting_table), 1);
}

static void *lcm_switch_mode(int mode)
{
#ifndef BUILD_LK
/* customization: 1. V2C config 2 values, C2V config 1 value; 2. config mode control register */
	if (mode == 0) {	/* V2C */
		lcm_switch_mode_cmd.mode = CMD_MODE;
		lcm_switch_mode_cmd.addr = 0xBB;	/* mode control addr */
		lcm_switch_mode_cmd.val[0] = 0x13;	/* enabel GRAM firstly, ensure writing one frame to GRAM */
		lcm_switch_mode_cmd.val[1] = 0x10;	/* disable video mode secondly */
	} else {		/* C2V */
		lcm_switch_mode_cmd.mode = SYNC_PULSE_VDO_MODE;
		lcm_switch_mode_cmd.addr = 0xBB;
		lcm_switch_mode_cmd.val[0] = 0x03;	/* disable GRAM and enable video mode */
	}
	return (void *)(&lcm_switch_mode_cmd);
#else
	return NULL;
#endif
}


struct LCM_DRIVER zte_mango_zhongguangdian_er68577_720p_5p45_boe_lcm_drv = {
	.name = "zte_mango_zhongguangdian_er68577_720p_5p45_boe_drv",
	.set_util_funcs = lcm_set_util_funcs,
	.get_params = lcm_get_params,
	.init = lcm_init,
	.suspend = lcm_suspend,
	.resume = lcm_resume,
	.compare_id = lcm_compare_id,
	.init_power = lcm_init_power,
	.resume_power = lcm_resume_power,
	.suspend_power = lcm_suspend_power,
	.esd_check = lcm_esd_check,
	.set_backlight_cmdq = lcm_setbacklight_cmdq,
	.ata_check = lcm_ata_check,
	.update = lcm_update,
	.switch_mode = lcm_switch_mode,
};
