#
# Makefile for the linux kernel.
#
#subdir-ccflags-y += -I$(srctree)/drivers/misc/mediatek/mtprof
subdir-ccflags-y += -Werror
ccflags-y := -fno-function-sections -fno-data-sections

ifdef CONFIG_MTPROF
ccflags-y += -Idrivers/misc/mediatek/mtprof/
endif

ifdef CONFIG_MTK_RAM_CONSOLE
ccflags-y += -Idrivers/misc/mediatek/include/
endif

obj-y                          := main.o version.o mounts.o
obj-y                          += noinitramfs.o
obj-$(CONFIG_BLK_DEV_INITRD)   += initramfs.o
obj-$(CONFIG_GENERIC_CALIBRATE_DELAY) += calibrate.o

ifneq ($(CONFIG_ARCH_INIT_TASK),y)
obj-y                          += init_task.o
endif

mounts-y			:= do_mounts.o
mounts-$(CONFIG_BLK_DEV_RAM)	+= do_mounts_rd.o
mounts-$(CONFIG_BLK_DEV_INITRD)	+= do_mounts_initrd.o
mounts-$(CONFIG_BLK_DEV_MD)	+= do_mounts_md.o
mounts-$(CONFIG_BLK_DEV_DM)	+= do_mounts_dm.o

ifeq (yes, $(strip $(MTK_BUILD_ROOT)))
mounts-y			+= do_mounts_post.o
endif

# dependencies on generated files need to be listed explicitly
$(obj)/version.o: include/generated/compile.h

# Original Z5157V build identity for KSU and opted-in stock builds.
ifneq ($(filter y 1,$(CONFIG_KSU) $(Z5157V_STOCK_UNAME)),)
override KBUILD_BUILD_VERSION := 1
override KBUILD_BUILD_TIMESTAMP := Fri Jun 16 10:31:59 CST 2023
override KBUILD_BUILD_USER := zte
override KBUILD_BUILD_HOST := scl_xa242_056
export KBUILD_BUILD_VERSION KBUILD_BUILD_TIMESTAMP
export KBUILD_BUILD_USER KBUILD_BUILD_HOST
endif

# compile.h changes depending on hostname, generation number, etc,
# so we regenerate it always.
# mkcompile_h will make sure to only update the
# actual file if its content has changed.

       chk_compile.h = :
 quiet_chk_compile.h = echo '  CHK     $@'
silent_chk_compile.h = :
include/generated/compile.h: FORCE
	@$($(quiet)chk_compile.h)
	$(Q)$(CONFIG_SHELL) $(srctree)/scripts/mkcompile_h $@ \
	"$(UTS_MACHINE)" "$(CONFIG_SMP)" "$(CONFIG_PREEMPT)" "$(CC) $(KBUILD_CFLAGS)"
