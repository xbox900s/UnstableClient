package de.mjadventure.tierlistmod.data;

import java.util.List;
import java.util.UUID;

public record PlayerProfile(
        long discordId,
        UUID uuid,
        String playerName,
        boolean tester,
        boolean verified,
        List<TierEntry> tiers
) {
    public boolean isOwner() {
        return uuid != null && uuid.toString().equalsIgnoreCase("1b170739-2776-4bd7-b64a-c094d4cb4422");
    }
}
