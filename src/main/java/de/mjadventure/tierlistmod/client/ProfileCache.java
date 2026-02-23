package de.mjadventure.tierlistmod.client;

import de.mjadventure.tierlistmod.data.DatabaseService;
import de.mjadventure.tierlistmod.data.PlayerProfile;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class ProfileCache {
    private final DatabaseService databaseService = new DatabaseService();
    private final Map<String, Optional<PlayerProfile>> byName = new ConcurrentHashMap<>();

    public Optional<PlayerProfile> getOrLoad(String playerName) {
        if (playerName == null || playerName.isBlank()) {
            return Optional.empty();
        }
        return byName.computeIfAbsent(playerName.toLowerCase(), k -> databaseService.loadProfileByName(playerName));
    }

    public DatabaseService db() {
        return databaseService;
    }

    public void invalidate(String name) {
        if (name == null) {
            return;
        }
        byName.remove(name.toLowerCase());
    }

    public void clear() {
        byName.clear();
    }
}
