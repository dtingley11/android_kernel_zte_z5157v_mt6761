#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define KERNEL_VERSION(a,b,c) (((a)<<16)|((b)<<8)|(c))
#define LINUX_VERSION_CODE KERNEL_VERSION(4,9,190)
typedef uint32_t u32;
struct av_decision {u32 allowed,auditallow,auditdeny,seqno,flags;};
static u32 latest_granting=1, avc_generation=1, netlink_generation=1, status_generation=1;
static int policy_rwlock,lock_depth,xfrm_updates;
static void write_lock_irq(int *lock) {assert(lock==&policy_rwlock&&!lock_depth);lock_depth++;}
static void write_unlock_irq(int *lock) {assert(lock==&policy_rwlock&&lock_depth==1);lock_depth--;}
static int avc_ss_reset(u32 seq) {assert(!lock_depth);if(seq>avc_generation)avc_generation=seq;return 0;}
static void selnl_notify_policyload(u32 seq) {assert(!lock_depth);if(seq>netlink_generation)netlink_generation=seq;}
static void selinux_status_update_policyload(u32 seq) {assert(!lock_depth);status_generation=seq;}
static void selinux_xfrm_notify_policyload(void) {assert(!lock_depth);xfrm_updates++;}
#include "actual-policy-sequence.inc"
static void check_decision(void) {
 struct av_decision decision;
 avd_init(&decision);
 assert(decision.seqno==latest_granting);
 assert(decision.seqno==avc_generation);
 assert(decision.seqno==netlink_generation);
 assert(decision.seqno==status_generation);
 assert(!decision.allowed&&!decision.auditallow&&decision.auditdeny==UINT32_MAX&&!decision.flags);
}
int main(void) {
 check_decision();
 /* Initial KSU rules and four module policy batches, matching the failed boot. */
 for(int i=0;i<5;i++){reset_avc_cache();check_decision();}
 assert(latest_granting==6&&xfrm_updates==5);
 /* A normal security-server update followed by further module changes. */
 latest_granting=100;
 avc_ss_reset(100);selnl_notify_policyload(100);selinux_status_update_policyload(100);
 for(int i=0;i<64;i++){reset_avc_cache();check_decision();}
 assert(latest_granting==164&&xfrm_updates==69);
 puts("PASS: KSU/module policy updates and server reloads keep decision, AVC, netlink and status generations synchronized");
}
