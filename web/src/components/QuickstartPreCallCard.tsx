"use client";

import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { VaayuMitraMark } from "@/components/QuickstartConversationLayout";

type QuickstartPreCallCardProps = {
	isLoading: boolean;
	error: string | null;
	onStartConversation: () => void;
	coords?: { lat: number; lon: number } | null;
	onToggleLocation?: () => void;
	isLocating?: boolean;
};

export function QuickstartPreCallCard({
	isLoading,
	error,
	onStartConversation,
	coords,
	onToggleLocation,
	isLocating = false,
}: QuickstartPreCallCardProps) {
	return (
		<div
			className="relative mx-auto flex w-[min(94vw,30rem)] animate-fade-up flex-col items-center overflow-hidden rounded-3xl border border-border px-8 py-9 text-center shadow-[0_24px_70px_rgba(0,0,0,0.5)]"
			style={{
				background:
					"linear-gradient(165deg, hsl(172 66% 50% / 0.12), transparent 42%), linear-gradient(210deg, hsl(38 92% 60% / 0.1), transparent 46%), linear-gradient(180deg, hsl(var(--surface-elevated)), hsl(var(--surface)))",
			}}
		>
			<div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-primary/20 blur-3xl" />
			<div className="pointer-events-none absolute -bottom-12 -left-10 h-40 w-40 rounded-full bg-accent/15 blur-3xl" />
			<div className="relative">
				<VaayuMitraMark size={56} />
				<span className="vm-pulse-ring absolute inset-0 rounded-2xl border border-primary/50" aria-hidden />
			</div>
			<p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.22em] text-primary">
				वायुमित्र · IMD-grounded
			</p>
			<h1 className="mt-1 text-3xl font-semibold leading-tight tracking-tight text-foreground">
				Talk to VaayuMitra
			</h1>
			<p className="mt-3 text-sm font-medium leading-6 text-muted-foreground">
				Bharat&apos;s voice-native मौसम intelligence — district forecasts,
				sea-state and cyclone alerts for farmers, fishermen, and disaster
				teams. No typing, no English needed.
			</p>
			<div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-[11px] font-medium">
				<span className="rounded-full border border-border bg-secondary/70 px-2.5 py-1 text-secondary-foreground">🌾 Farmer</span>
				<span className="rounded-full border border-border bg-secondary/70 px-2.5 py-1 text-secondary-foreground">🎣 Fisherman</span>
				<span className="rounded-full border border-border bg-secondary/70 px-2.5 py-1 text-secondary-foreground">🚨 Disaster</span>
				<span className="rounded-full border border-primary/40 bg-primary/10 px-2.5 py-1 text-primary">✓ IMD cited</span>
			</div>

			{onToggleLocation ? (
				<button
					type="button"
					onClick={onToggleLocation}
					disabled={isLoading || isLocating}
					className="mt-4 flex items-center gap-2 rounded-full border border-border/70 bg-secondary/50 px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-secondary"
					aria-label="Toggle GPS auto-location"
				>
					{isLocating ? (
						<>
							<Loader2 className="h-3 w-3 animate-spin text-primary" />
							<span>Detecting GPS...</span>
						</>
					) : coords ? (
						<>
							<span className="text-emerald-400">📍</span>
							<span>GPS: {coords.lat.toFixed(2)}°N, {coords.lon.toFixed(2)}°E</span>
						</>
					) : (
						<>
							<span className="text-muted-foreground">📍</span>
							<span>Enable GPS Auto-Location</span>
						</>
					)}
				</button>
			) : null}

			<Button
				onClick={onStartConversation}
				disabled={isLoading}
				className="relative z-10 mt-7 h-11 w-full rounded-xl bg-primary text-sm font-semibold text-primary-foreground shadow-[0_10px_30px_hsl(172_66%_50%/0.3)] hover:brightness-110 disabled:opacity-70"
				aria-label={
					isLoading
						? "Starting conversation with AI agent"
						: "Start conversation with AI agent"
				}
			>
				{isLoading ? (
					<>
						<Loader2 className="h-4 w-4 animate-spin" />
						Starting...
					</>
				) : (
					"Start Conversation"
				)}
			</Button>
			{error ? <p className="mt-3 text-xs text-destructive">{error}</p> : null}
		</div>
	);
}
