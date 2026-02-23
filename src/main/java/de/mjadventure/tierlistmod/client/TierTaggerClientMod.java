package de.mjadventure.tierlistmod.client;

import com.mojang.brigadier.arguments.StringArgumentType;
import de.mjadventure.tierlistmod.data.DatabaseService;
import de.mjadventure.tierlistmod.data.PlayerProfile;
import de.mjadventure.tierlistmod.data.TierEntry;
import de.mjadventure.tierlistmod.data.TierFormatting;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandManager;
import net.fabricmc.fabric.api.client.command.v2.ClientCommandRegistrationCallback;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.AbstractClientPlayerEntity;
import net.minecraft.text.MutableText;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;

import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public class TierTaggerClientMod implements ClientModInitializer {
    public static final ProfileCache CACHE = new ProfileCache();

    @Override
    public void onInitializeClient() {
        ClientPlayConnectionEvents.JOIN.register((handler, sender, client) -> CACHE.clear());
        ClientTickEvents.END_CLIENT_TICK.register(this::decoratePlayerNames);

        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) -> dispatcher.register(
                ClientCommandManager.literal("tier")
                        .then(ClientCommandManager.argument("player", StringArgumentType.word())
                                .executes(context -> {
                                    showTierProfile(context.getSource().getClient(), StringArgumentType.getString(context, "player"));
                                    return 1;
                                }))
        ));

        ClientCommandRegistrationCallback.EVENT.register((dispatcher, registryAccess) -> dispatcher.register(
                ClientCommandManager.literal("verify")
                        .then(ClientCommandManager.argument("code", StringArgumentType.word())
                                .executes(context -> {
                                    runVerify(context.getSource().getClient(), StringArgumentType.getString(context, "code"));
                                    return 1;
                                }))
        ));
    }

    private void runVerify(MinecraftClient client, String code) {
        if (client.player == null) {
            return;
        }

        String name = client.player.getName().getString();
        UUID uuid = client.player.getUuid();
        DatabaseService.VerifyResult result = CACHE.db().verifyByCode(code, name, uuid);
        switch (result) {
            case OK -> {
                CACHE.invalidate(name);
                client.player.sendMessage(Text.literal("Verifizierung erfolgreich! ✔").formatted(Formatting.GREEN), false);
            }
            case CODE_NOT_FOUND -> client.player.sendMessage(Text.literal("Code nicht gefunden.").formatted(Formatting.RED), false);
            case CODE_EXPIRED -> client.player.sendMessage(Text.literal("Code ist abgelaufen (15 Minuten).").formatted(Formatting.RED), false);
            case ERROR -> client.player.sendMessage(Text.literal("Datenbankfehler bei der Verifizierung.").formatted(Formatting.DARK_RED), false);
        }
    }

    private void decoratePlayerNames(MinecraftClient client) {
        if (client.world == null) {
            return;
        }

        for (AbstractClientPlayerEntity player : client.world.getPlayers()) {
            CACHE.getOrLoad(player.getName().getString()).ifPresent(profile -> {
                player.setCustomName(buildOverheadLabel(profile));
                player.setCustomNameVisible(true);
            });
        }
    }

    private Text buildOverheadLabel(PlayerProfile profile) {
        TierEntry primary = profile.tiers().isEmpty() ? null : profile.tiers().get(0);

        MutableText line = Text.empty();
        if (profile.isOwner()) {
            line.append(Text.literal("Owner\n").formatted(Formatting.RED, Formatting.BOLD));
        } else if (profile.tester()) {
            line.append(Text.literal("Tester!\n").formatted(Formatting.LIGHT_PURPLE, Formatting.BOLD));
        }

        line.append(Text.literal(profile.playerName()).formatted(Formatting.WHITE));
        if (profile.verified()) {
            line.append(verifyCheck(profile));
        }
        if (primary != null) {
            line.append(TierFormatting.asBadge(primary.tier()));
        }

        return line;
    }

    private MutableText verifyCheck(PlayerProfile profile) {
        if (profile.isOwner()) {
            return Text.literal(" ✔").formatted(Formatting.RED, Formatting.BOLD);
        }
        if (profile.tester()) {
            return Text.literal(" ✔").formatted(Formatting.LIGHT_PURPLE, Formatting.BOLD);
        }
        return Text.literal(" ✔").formatted(Formatting.GREEN, Formatting.BOLD);
    }

    private void showTierProfile(MinecraftClient client, String playerName) {
        if (client.player == null) {
            return;
        }

        Optional<PlayerProfile> optional = CACHE.getOrLoad(playerName);
        if (optional.isEmpty()) {
            client.player.sendMessage(Text.literal("Kein Profil gefunden für " + playerName).formatted(Formatting.RED), false);
            return;
        }

        PlayerProfile profile = optional.get();
        client.player.sendMessage(Text.literal("§8§m--------------------------------"), false);
        MutableText header = Text.literal("Profil: ").formatted(Formatting.GRAY)
                .append(Text.literal(profile.playerName()).formatted(Formatting.WHITE, Formatting.BOLD));
        if (profile.isOwner()) {
            header.append(Text.literal("  [Owner]").formatted(Formatting.RED));
        } else if (profile.tester()) {
            header.append(Text.literal("  [Tester]").formatted(Formatting.LIGHT_PURPLE));
        }
        client.player.sendMessage(header, false);

        List<TierEntry> entries = profile.tiers().stream().sorted(Comparator.comparing(TierEntry::mode)).toList();
        for (TierEntry entry : entries) {
            client.player.sendMessage(Text.literal(" - " + entry.mode() + ": ").formatted(Formatting.DARK_GRAY)
                    .append(TierFormatting.asBadge(entry.tier())), false);
        }

        if (entries.isEmpty()) {
            client.player.sendMessage(Text.literal("Keine gerankten Modi vorhanden.").formatted(Formatting.GRAY), false);
        }

        client.player.sendMessage(Text.literal("§8§m--------------------------------"), false);
    }
}
