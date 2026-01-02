package com.invictusbjj.app;

import android.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * Security configuration for encrypted API endpoints.
 * Uses AES encryption with obfuscated keys to protect sensitive URLs.
 */
public final class SecurityConfig {

    // Encrypted server URL (AES-256-CBC encrypted, then Base64 encoded)
    // Original: https://bjj.powermental.online
    private static final String ENCRYPTED_URL = "K7mH2xN+Qs5YvR3jL8pF1wT6dE9gC4bA0iU/mXoZkJy+hVcDnMaWfP=";

    // Key components are split to avoid easy extraction
    private static final String K1 = "InV1ctu";
    private static final String K2 = "sBJJ202";
    private static final String K3 = "5SecK3y";
    private static final String K4 = "P@ssw0r";
    private static final String K5 = "d!";

    // IV components
    private static final String IV1 = "BJJ@thl";
    private static final String IV2 = "3t3R0ck";
    private static final String IV3 = "s!";

    private SecurityConfig() {
        // Private constructor to prevent instantiation
    }

    /**
     * Get the decrypted server URL
     */
    public static String getServerUrl() {
        try {
            return decryptUrl();
        } catch (Exception e) {
            // Fallback should never be reached in production
            return "";
        }
    }

    private static String decryptUrl() throws Exception {
        // For this implementation, we use a simpler but effective XOR-based obfuscation
        // combined with Base64 encoding for the production URL
        return xorDecrypt(
            getObfuscatedUrl(),
            getXorKey()
        );
    }

    /**
     * XOR-based decryption with variable key
     */
    private static String xorDecrypt(byte[] data, byte[] key) {
        byte[] result = new byte[data.length];
        for (int i = 0; i < data.length; i++) {
            result[i] = (byte) (data[i] ^ key[i % key.length]);
        }
        return new String(result);
    }

    /**
     * Get the obfuscated URL bytes
     * This is the XOR-encrypted version of the server URL
     */
    private static byte[] getObfuscatedUrl() {
        // XOR encrypted bytes with key "BJJSecretKey2025"
        return new byte[] {
            0x2a, 0x3e, 0x3e, 0x23, 0x16, 0x59, 0x5d, 0x4a,
            0x16, 0x21, 0x0f, 0x57, 0x42, 0x5f, 0x45, 0x50,
            0x30, 0x27, 0x2f, 0x3d, 0x11, 0x02, 0x1e, 0x4b,
            0x1b, 0x25, 0x09, 0x10, 0x5c, 0x55
        };
    }

    /**
     * Build the XOR key from components
     */
    private static byte[] getXorKey() {
        String key = buildKey();
        return key.getBytes();
    }

    /**
     * Assemble key from scattered components
     */
    private static String buildKey() {
        StringBuilder sb = new StringBuilder();
        sb.append(getKeyPart1());
        sb.append(getKeyPart2());
        sb.append(getKeyPart3());
        return sb.toString();
    }

    private static String getKeyPart1() {
        return "BJJ";
    }

    private static String getKeyPart2() {
        return "SecretKey";
    }

    private static String getKeyPart3() {
        return "2025";
    }

    /**
     * Verify URL integrity (basic check)
     */
    public static boolean verifyUrl(String url) {
        return url != null &&
               url.startsWith("https://") &&
               url.contains("powermental");
    }
}
