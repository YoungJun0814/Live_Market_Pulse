import L from "leaflet";
import { useEffect } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";

import type { FocusRegionEvent } from "../types";

interface WorldMapProps {
  events: FocusRegionEvent[];
  onCountrySelect: (country: string) => void;
}

const pulseIcon = L.divIcon({
  className: "pulse-icon",
  html: '<div class="pulse-ring"></div><div class="pulse-core"></div>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

interface MapViewportControllerProps {
  latest?: FocusRegionEvent;
}

function MapViewportController({ latest }: MapViewportControllerProps) {
  const map = useMap();

  useEffect(() => {
    if (!latest) {
      return;
    }

    map.flyTo([latest.lat, latest.lon], 4, {
      animate: true,
      duration: 1.4,
    });
  }, [latest?.city, latest?.country, latest?.lat, latest?.lon, latest?.timestamp, map]);

  return null;
}

export function WorldMap({ events, onCountrySelect }: WorldMapProps) {
  const latest = events[0];
  const latestLabel =
    latest == null
      ? "Monitoring"
      : Math.abs(latest.sentiment_score) >= 60
        ? "High Alert"
        : Math.abs(latest.sentiment_score) >= 30
          ? "Elevated"
          : "Monitoring";

  return (
    <section className="panel panel--map">
      <div className="panel__heading">
        <p className="eyebrow">Zone 1 - RSS Event Markers</p>
        <h2>Focus Region Map</h2>
      </div>
      <div className="map-shell">
        <div className="map-shell__status">
          <span className="map-shell__status-pill">{latestLabel}</span>
          <p>
            {latest
              ? `${latest.city}, ${latest.country} highlighted by autopilot.`
              : "Waiting for a geopolitical or policy shock with coordinates."}
          </p>
        </div>
        <MapContainer
          center={[25, 5]}
          zoom={2}
          minZoom={2}
          scrollWheelZoom={false}
          className="world-map"
        >
          <MapViewportController latest={latest} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />
          {events.slice(0, 8).map((event, index) => (
            <CircleMarker
              key={`${event.country}-${event.timestamp ?? index}-${index}`}
              center={[event.lat, event.lon]}
              radius={Math.max(8, 16 - index)}
              pathOptions={{
                color: event.sentiment_score >= 0 ? "#64f0b9" : "#ff6d6d",
                fillColor: event.sentiment_score >= 0 ? "#64f0b9" : "#ff6d6d",
                fillOpacity: 0.22,
                weight: 1.5,
              }}
              eventHandlers={{
                click: () => onCountrySelect(event.country),
              }}
            >
              <Popup>
                <strong>{event.city}, {event.country}</strong>
                <br />
                {event.trigger_signal}
              </Popup>
            </CircleMarker>
          ))}
          {latest ? (
            <Marker
              position={[latest.lat, latest.lon]}
              icon={pulseIcon}
              eventHandlers={{
                click: () => onCountrySelect(latest.country),
              }}
            />
          ) : null}
        </MapContainer>
        <div className="map-shell__legend">
          <span className="legend-dot legend-dot--monitor" />
          Monitoring
          <span className="legend-dot legend-dot--bullish" />
          Positive
          <span className="legend-dot legend-dot--bearish" />
          Negative
        </div>
      </div>
    </section>
  );
}
