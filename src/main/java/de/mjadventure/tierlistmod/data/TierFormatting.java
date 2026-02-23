package de.mjadventure.tierlistmod.data;

import net.minecraft.text.MutableText;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;

public final class TierFormatting {
    private TierFormatting() {}

    public static MutableText asBadge(String tier) {
        Formatting color = switch (normalized(tier)) {
            case "HT1" -> Formatting.DARK_RED;
            case "HT2" -> Formatting.RED;
            case "HT3" -> Formatting.GOLD;
            case "HT4" -> Formatting.YELLOW;
            case "HT5" -> Formatting.GREEN;
            case "LT1" -> Formatting.DARK_PURPLE;
            case "LT2" -> Formatting.LIGHT_PURPLE;
            case "LT3" -> Formatting.AQUA;
            case "LT4" -> Formatting.BLUE;
            case "LT5" -> Formatting.GRAY;
            default -> Formatting.DARK_GRAY;
        };

        String icon = normalized(tier).startsWith("HT") ? "▲" : normalized(tier).startsWith("LT") ? "◆" : "•";
        return Text.literal(" [" + icon + " " + normalized(tier) + "]").formatted(color, Formatting.BOLD);
    }

    private static String normalized(String value) {
        return value == null ? "" : value.toUpperCase();
    }
}
