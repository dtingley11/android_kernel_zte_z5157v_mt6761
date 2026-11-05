# Stock kernel identity

KSU and KSU+SUSFS builds use the release and build version extracted from
the supplied Z5157V stock boot image:

```text
4.9.190+
#1 SMP PREEMPT Fri Jun 16 10:31:59 CST 2023
```

The reference boot image SHA-256 is
`80a0d09f04215e2b4e54c3eaa120ff325630f64f3f73e7eac7881c06c844e526`.
These are the actual kernel UTS fields. The build also uses the original
`zte` build user and `scl_xa242_056` build host. Android controls the hostname;
the phone reports `localhost`, and ARM setup supplies `armv7l`.

Stock builds keep their normal build identity by default. Enable
`stock_uname` when manually starting either build workflow to select the
original identity. For local stock builds, use `--stock-uname` with
`ci/build.py build`, or pass `Z5157V_STOCK_UNAME=1` to make.

Build reports record the selected mode and compiled release/version.
Packages using the original identity end in `-stock-uname.zip`.
SUSFS can still override uname if explicitly configured to do so.
