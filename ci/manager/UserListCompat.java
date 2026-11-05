package com.dergoogler.mmrl.platform.hiddenApi;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.List;

/** Supports both Android's legacy and modern IUserManager contracts. */
public final class UserListCompat {
    private UserListCompat() {}

    @SuppressWarnings("unchecked")
    public static <T> List<T> getUsers(Object manager, Class<?> contract)
            throws ReflectiveOperationException {
        Method method;
        Object[] args;
        try {
            method = contract.getMethod("getUsers", boolean.class, boolean.class, boolean.class);
            args = new Object[] {true, true, true};
        } catch (NoSuchMethodException modernUnavailable) {
            // Android 10 and earlier accept only excludeDying.
            method = contract.getMethod("getUsers", boolean.class);
            args = new Object[] {true};
        }
        try {
            return (List<T>) method.invoke(manager, args);
        } catch (InvocationTargetException invocation) {
            Throwable cause = invocation.getCause();
            if (cause instanceof RuntimeException) throw (RuntimeException) cause;
            if (cause instanceof Error) throw (Error) cause;
            throw invocation;
        }
    }
}
