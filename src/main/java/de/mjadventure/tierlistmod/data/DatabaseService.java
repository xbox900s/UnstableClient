package de.mjadventure.tierlistmod.data;

import com.mojang.logging.LogUtils;
import org.slf4j.Logger;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public class DatabaseService {
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final Duration VERIFY_WINDOW = Duration.ofMinutes(15);

    private static final String JDBC_URL = "jdbc:mysql://dbs.mjadventurehost.de:3306/s483_TierList?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC";
    private static final String USER = "u483_C3zolNOIV5";
    private static final String PASSWORD = "36m8598KC5SgBZkt.s9^H@ho";

    public Optional<PlayerProfile> loadProfileByName(String minecraftName) {
        String sql = """
                SELECT * FROM TierModDB
                WHERE LOWER(minecraft_name) = LOWER(?)
                  AND is_blacklisted = 0
                LIMIT 1
                """;

        try (Connection connection = DriverManager.getConnection(JDBC_URL, USER, PASSWORD);
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, minecraftName);
            try (ResultSet resultSet = statement.executeQuery()) {
                if (!resultSet.next()) {
                    return Optional.empty();
                }
                return Optional.of(parseProfile(resultSet));
            }
        } catch (SQLException ex) {
            LOGGER.error("Tier DB query failed for {}", minecraftName, ex);
            return Optional.empty();
        }
    }

    public VerifyResult verifyByCode(String code, String minecraftName, UUID uuid) {
        if (code == null || code.isBlank() || minecraftName == null || minecraftName.isBlank()) {
            return VerifyResult.INVALID_INPUT;
        }

        String lookup = """
                SELECT discord_id, verify_code_created_at
                FROM TierModDB
                WHERE verify_code = ?
                  AND is_blacklisted = 0
                LIMIT 1
                """;

        String update = """
                UPDATE TierModDB
                SET minecraft_name = ?, minecraft_uuid = ?, linked_at = NOW(), link_source = 'verify',
                    verify_code = NULL, verify_code_created_at = NULL
                WHERE discord_id = ?
                """;

        try (Connection connection = DriverManager.getConnection(JDBC_URL, USER, PASSWORD)) {
            connection.setAutoCommit(false);
            try (PreparedStatement lookupStmt = connection.prepareStatement(lookup)) {
                lookupStmt.setString(1, code.trim());
                try (ResultSet rs = lookupStmt.executeQuery()) {
                    if (!rs.next()) {
                        connection.rollback();
                        return VerifyResult.CODE_NOT_FOUND;
                    }

                    Timestamp created = rs.getTimestamp("verify_code_created_at");
                    if (created == null || created.toInstant().isBefore(Instant.now().minus(VERIFY_WINDOW))) {
                        connection.rollback();
                        return VerifyResult.CODE_EXPIRED;
                    }

                    long discordId = rs.getLong("discord_id");
                    try (PreparedStatement updateStmt = connection.prepareStatement(update)) {
                        updateStmt.setString(1, minecraftName.trim());
                        updateStmt.setString(2, uuid == null ? null : uuid.toString());
                        updateStmt.setLong(3, discordId);
                        updateStmt.executeUpdate();
                    }

                    connection.commit();
                    return VerifyResult.OK;
                }
            } catch (SQLException e) {
                connection.rollback();
                throw e;
            }
        } catch (SQLException ex) {
            LOGGER.error("Verify failed for {}", minecraftName, ex);
            return VerifyResult.ERROR;
        }
    }

    private PlayerProfile parseProfile(ResultSet rs) throws SQLException {
        long discordId = rs.getLong("discord_id");
        String name = rs.getString("minecraft_name");
        String uuidText = rs.getString("minecraft_uuid");

        UUID uuid = null;
        if (uuidText != null && !uuidText.isBlank()) {
            try {
                uuid = UUID.fromString(uuidText);
            } catch (IllegalArgumentException ignored) {
                uuid = null;
            }
        }

        List<TierEntry> tiers = new ArrayList<>();
        addTier(tiers, "Crystal", rs.getString("tier_crystal"));
        addTier(tiers, "Sword", rs.getString("tier_sword"));
        addTier(tiers, "Axe", rs.getString("tier_axe"));
        addTier(tiers, "NethPot", rs.getString("tier_nethpot"));
        addTier(tiers, "Pot", rs.getString("tier_pot"));
        addTier(tiers, "UHC", rs.getString("tier_uhc"));
        addTier(tiers, "SMP", rs.getString("tier_smp"));

        boolean tester = safeBool(rs, "is_tester");
        boolean verified = name != null && !name.isBlank();
        return new PlayerProfile(discordId, uuid, name, tester, verified, tiers);
    }

    private static boolean safeBool(ResultSet rs, String column) {
        try {
            return rs.getBoolean(column);
        } catch (SQLException ignored) {
            return false;
        }
    }

    private static void addTier(List<TierEntry> tiers, String mode, String tierValue) {
        if (tierValue == null || tierValue.isBlank() || tierValue.equalsIgnoreCase("unranked")) {
            return;
        }
        tiers.add(new TierEntry(mode, tierValue));
    }

    public enum VerifyResult {
        OK,
        CODE_NOT_FOUND,
        CODE_EXPIRED,
        INVALID_INPUT,
        ERROR
    }
}
