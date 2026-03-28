import React from "react";
import { InputStream, Rescaler, Text, View } from "@swmansion/smelter";

export interface MarketOverlaySceneProps {
  inputId: string;
  sentimentScore: number;
  overallSentiment: string;
  headline: string;
  reasoning: string;
  timestamp?: string;
}

function toneColors(sentimentScore: number) {
  if (sentimentScore > 20) {
    return {
      accent: "#2CE0A7FF",
      surface: "#0E1C21CC",
    };
  }
  if (sentimentScore < -20) {
    return {
      accent: "#FF6B6BFF",
      surface: "#231417CC",
    };
  }
  return {
    accent: "#F9C74FFF",
    surface: "#201D12CC",
  };
}

export function MarketOverlayScene({
  inputId,
  sentimentScore,
  overallSentiment,
  headline,
  reasoning,
  timestamp,
}: MarketOverlaySceneProps) {
  const colors = toneColors(sentimentScore);
  const scoreLabel = `${sentimentScore >= 0 ? "+" : ""}${sentimentScore}`;

  return (
    <View
      style={{
        width: 1920,
        height: 1080,
        backgroundColor: "#071019FF",
      }}
    >
      <Rescaler
        style={{
          width: 1920,
          height: 1080,
          rescaleMode: "fill",
        }}
      >
        <InputStream inputId={inputId} />
      </Rescaler>

      <View
        style={{
          top: 32,
          left: 32,
          width: 460,
          padding: 24,
          borderRadius: 24,
          backgroundColor: "#08111BCC",
          borderWidth: 2,
          borderColor: colors.accent,
        }}
      >
        <Text
          style={{
            fontSize: 28,
            color: "#9CC3FFFF",
            fontFamily: "Verdana",
            fontWeight: "bold",
          }}
        >
          LIVE MARKET PULSE
        </Text>
        <View style={{ paddingTop: 12 }}>
          <Text
            style={{
              fontSize: 92,
              lineHeight: 92,
              color: colors.accent,
              fontFamily: "Verdana",
              fontWeight: "bold",
            }}
          >
            {scoreLabel}
          </Text>
        </View>
        <Text
          style={{
            fontSize: 32,
            color: "#FFFFFFFF",
            fontFamily: "Verdana",
            fontWeight: "bold",
          }}
        >
          {overallSentiment}
        </Text>
      </View>

      <View
        style={{
          right: 32,
          top: 32,
          width: 700,
          padding: 20,
          borderRadius: 20,
          backgroundColor: colors.surface,
          borderWidth: 1,
          borderColor: "#3B5A75FF",
        }}
      >
        <Text
          style={{
            fontSize: 24,
            color: "#8FB8E8FF",
            fontFamily: "Verdana",
            fontWeight: "bold",
          }}
        >
          AI ANALYSIS
        </Text>
        <View style={{ paddingTop: 10 }}>
          <Text
            style={{
              fontSize: 30,
              lineHeight: 36,
              color: "#FFFFFFFF",
              fontFamily: "Verdana",
              wrap: "word",
              maxWidth: 660,
            }}
          >
            {reasoning}
          </Text>
        </View>
      </View>

      <View
        style={{
          left: 40,
          right: 40,
          bottom: 40,
          padding: 22,
          borderRadius: 24,
          backgroundColor: "#07111BE6",
          borderWidth: 1,
          borderColor: "#29435BFF",
        }}
      >
        <Text
          style={{
            fontSize: 22,
            color: colors.accent,
            fontFamily: "Verdana",
            fontWeight: "bold",
          }}
        >
          BREAKING
        </Text>
        <View style={{ paddingTop: 8 }}>
          <Text
            style={{
              fontSize: 42,
              lineHeight: 48,
              color: "#FFFFFFFF",
              fontFamily: "Verdana",
              fontWeight: "bold",
              wrap: "word",
              maxWidth: 1750,
            }}
          >
            {headline}
          </Text>
        </View>
        <View style={{ paddingTop: 10 }}>
          <Text
            style={{
              fontSize: 18,
              color: "#87A3C0FF",
              fontFamily: "Verdana",
            }}
          >
            {timestamp ? `Updated ${timestamp}` : "Awaiting live overlay refresh"}
          </Text>
        </View>
      </View>
    </View>
  );
}
