"use client";

import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

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
			className="mx-auto flex w-[min(92vw,26.25rem)] animate-fade-up flex-col items-center rounded-[20px] border border-[#2b2b2b] px-10 py-10 text-center shadow-[0_10px_24px_rgba(0,0,0,0.28)]"
			style={{
				backgroundImage:
					"linear-gradient(164.988deg, rgba(54,54,54,0.2) 1.0596%, rgba(0,0,0,0) 96.089%), linear-gradient(90deg, rgb(16,16,16) 0%, rgb(16,16,16) 100%)",
			}}
		>
			<h1 className="text-[28px] font-medium leading-[1.2] text-white">
				Talk to WeatherGPT
			</h1>
			<p className="mt-[14px] text-sm font-medium leading-6 text-muted-foreground">
				IMD-grounded voice weather for farmers, fishermen, and disaster
				managers — powered by Agora&apos;s Conversational AI engine.
			</p>

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
				className="mt-8 h-10 w-full rounded-lg border border-primary bg-primary text-sm font-medium text-black hover:border-white hover:bg-white hover:text-black disabled:hover:border-primary disabled:hover:bg-primary disabled:hover:text-black"
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
