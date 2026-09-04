"use client";

import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";

import { getCycloneMap, type CycloneMapData } from "@/services/api";

type CycloneMapPanelProps = {
  /** True while the agent TTS is speaking — cone highlight syncs to voice state. */
  speaking: boolean;
};

function coneStyle(speaking: boolean): L.PathOptions {
  return {
    color: speaking ? "#dc2626" : "#f97316",
    weight: speaking ? 4 : 2,
    fillColor: "#dc2626",
    fillOpacity: speaking ? 0.35 : 0.15,
  };
}

const TRACK_STYLE: L.PathOptions = {
  color: "#2563eb",
  weight: 3,
  dashArray: "6 4",
};

/**
 * CycloneMapPanel — plan.md Step 6.2 map sync.
 * Draws IMD cyclonewind MultiPolygon/cone + forecast track on Leaflet in
 * real time; the cone highlight pulses while the agent is speaking.
 * Circle markers only (no image assets, so no broken-icon issue on deploy).
 */
export function CycloneMapPanel({ speaking }: CycloneMapPanelProps) {
  const divRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.GeoJSON | null>(null);
  const speakingRef = useRef(speaking);
  speakingRef.current = speaking;

  const [data, setData] = useState<CycloneMapData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const el = divRef.current;
    if (!el || mapRef.current) return;
    const map = L.map(el, { attributionControl: true }).setView([16, 86], 4);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 10,
      attribution: "© OpenStreetMap · IMD",
    }).addTo(map);
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const next = await getCycloneMap();
        if (!cancelled) {
          setData(next);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Map load failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !data) return;
    layerRef.current?.remove();
    const layer = L.geoJSON(data as unknown as GeoJSON.GeoJsonObject, {
      style: (feature) =>
        feature?.properties?.kind === "cone" ? coneStyle(speakingRef.current) : TRACK_STYLE,
      pointToLayer: (_feature, latlng) =>
        L.circleMarker(latlng, {
          radius: 8,
          color: "#dc2626",
          weight: 3,
          fillColor: "#dc2626",
          fillOpacity: 0.9,
        }),
    }).addTo(map);
    layerRef.current = layer;
    try {
      const bounds = layer.getBounds();
      if (bounds.isValid()) map.fitBounds(bounds.pad(0.25));
    } catch {
      // Partial IMD payload: keep default Bay of Bengal view.
    }
  }, [data]);

  useEffect(() => {
    layerRef.current?.setStyle((feature) =>
      feature?.properties?.kind === "cone" ? coneStyle(speaking) : TRACK_STYLE,
    );
  }, [speaking, data]);

  const position = data?.features.find((f) => f.properties.kind === "position");

  return (
    <section
      className={`flex w-full flex-col gap-2 rounded-2xl border bg-card/20 px-4 py-3 transition-colors ${
        speaking ? "border-destructive/60" : "border-border"
      }`}
      aria-label="Cyclone cone map"
      aria-live="polite"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">Cyclone Cone</h2>
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
            speaking ? "bg-destructive/15 text-destructive" : "bg-muted text-muted-foreground"
          }`}
        >
          {loading ? "loading…" : speaking ? "● agent speaking" : "IMD live track"}
        </span>
      </div>
      <div ref={divRef} className="h-64 w-full overflow-hidden rounded-xl" role="img" aria-label="IMD cyclone track and cone of uncertainty map" />
      {error ? (
        <button
          type="button"
          className="text-left text-xs text-destructive underline"
          onClick={() => window.location.reload()}
          title={error}
        >
          Map failed to load ({error}) — retry
        </button>
      ) : (
        <p className="text-[11px] leading-4 text-muted-foreground">
          {data?.cyclone_name ?? "—"}
          {position?.properties.category ? ` · ${position.properties.category}` : ""}
          {position?.properties.msw_kts ? ` · ${position.properties.msw_kts} kt` : ""}
          {data?.cached_at ? ` · updated ${data.cached_at}` : ""} · IMD cyclonewind
        </p>
      )}
    </section>
  );
}
