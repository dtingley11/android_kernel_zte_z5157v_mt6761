package com.dergoogler.mmrl.platform.hiddenApi;

import java.util.Collections;
import java.util.List;

public final class UserListCompatTest {
    public interface Legacy { List<String> getUsers(boolean excludeDying); }
    public interface Modern { List<String> getUsers(boolean partial, boolean dying, boolean preCreated); }
    public interface Both extends Legacy, Modern {}
    public interface Missing {}
    public static class LegacyService implements Legacy {
        public List<String> getUsers(boolean dying) {
            if (!dying) throw new AssertionError("legacy filter lost");
            return Collections.singletonList("legacy");
        }
    }
    public static class ModernService implements Both {
        public List<String> getUsers(boolean p, boolean d, boolean c) {
            if (!p || !d || !c) throw new AssertionError("modern filters lost");
            return Collections.singletonList("modern");
        }
        public List<String> getUsers(boolean d) { throw new AssertionError("wrong overload"); }
    }
    public static class DeniedService implements Both {
        final SecurityException denial = new SecurityException("denied");
        public List<String> getUsers(boolean p, boolean d, boolean c) { throw denial; }
        public List<String> getUsers(boolean d) { throw new AssertionError("permission failure must not fall back"); }
    }
    public static void main(String[] args) throws Exception {
        if (!UserListCompat.getUsers(new LegacyService(), Legacy.class).equals(Collections.singletonList("legacy")))
            throw new AssertionError("legacy result");
        if (!UserListCompat.getUsers(new ModernService(), Modern.class).equals(Collections.singletonList("modern")))
            throw new AssertionError("modern result");
        if (!UserListCompat.getUsers(new ModernService(), Both.class).equals(Collections.singletonList("modern")))
            throw new AssertionError("modern should be preferred");
        try {
            UserListCompat.getUsers(new Object(), Missing.class);
            throw new AssertionError("missing method must be reported");
        } catch (NoSuchMethodException expected) {}
        DeniedService denied = new DeniedService();
        try {
            UserListCompat.getUsers(denied, Both.class);
            throw new AssertionError("permission denial lost");
        } catch (SecurityException expected) {
            if (expected != denied.denial) throw new AssertionError("permission exception changed");
        }
        System.out.println("PASS: legacy, modern, dual-overload, missing API and permission-denial cases");
    }
}
