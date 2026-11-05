# Z5157V ADB install and uninstall restore

Builds a root module for the reviewed Z5157V Android 10 firmware. It removes the
production-build rejections in `PackageManagerShellCommand.runInstall()` and
`runUninstall()` while retaining APK signature, permission and session checks. Other commands and
`ro.build.type` are unchanged.

```sh
adb pull /system/framework/services.jar services.jar
python3 tools/zte-adb-install/build.py --services services.jar --out adb-install-module
```

The builder requires the exact reviewed JAR checksum. It changes two two-byte
DEX instructions, regenerates that DEX's checksums and leaves all other JAR
entries unchanged. Use the original JAR when rebuilding after v1 is active; the
v2 installer accepts the original or v1-patched firmware. Firmware binaries are
supplied locally and are not committed.

Install the resulting ZIP as a KernelSU/Magisk module and reboot. Its early
boot script bind-mounts the patched framework file; it does not write `/system`.
It has not been reboot-tested. Test the experimental kernel separately before
installing this module. Disable or remove the module to restore the original
framework on the next boot; recovery can remove
`/data/adb/modules/zte_adb_install_restore` if Android cannot start.
