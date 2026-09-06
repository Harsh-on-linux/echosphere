"use client";

import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

export function VaayuMitraMark({ size = 40 }: { size?: number }) {
	return (
		<span
			aria-hidden
			className="relative grid shrink-0 place-items-center rounded-2xl"
			style={{
				width: size,
				height: size,
				background:
					"linear-gradient(135deg, hsl(172 66% 50% / 0.25), hsl(38 92% 60% / 0.18)), hsl(var(--surface-elevated))",
				border: "1px solid hsl(var(--border))",
			}}
		>
			<svg width={size * 0.6} height={size * 0.6} viewBox="0 0 100 100" fill="none">
				<path d="M18 40h36a13 13 0 1 0-13-13" stroke="hsl(172 66% 55%)" strokeWidth="9" strokeLinecap="round" />
				<path d="M18 60h52a13 13 0 1 1-13 13" stroke="hsl(38 92% 62%)" strokeWidth="9" strokeLinecap="round" />
				<circle cx="74" cy="30" r="7" fill="hsl(38 92% 62%)" />
			</svg>
		</span>
	);
}

type QuickstartConversationLayoutProps = {
	statusPanel: ReactNode;
	pipelineMetrics: ReactNode;
	transcriptPanel: ReactNode;
	visualizer: ReactNode;
	controls: ReactNode;
	metricsOverlay?: ReactNode;
	onEndConversation: () => void;
	/** Phase 2: IMD source attribution card under the transcript (optional). */
	imdSourceCard?: ReactNode;
	/** Phase 6.2: cyclone cone map under the source card (optional). */
	mapPanel?: ReactNode;
};

export function QuickstartConversationLayout({
	statusPanel,
	pipelineMetrics,
	transcriptPanel,
	visualizer,
	controls,
	metricsOverlay,
	onEndConversation,
	imdSourceCard,
	mapPanel,
}: QuickstartConversationLayoutProps) {
	return (
		<div className="flex min-h-0 flex-1 flex-col text-left">
			<header className="flex shrink-0 flex-col gap-4 border-b border-border px-4 py-4 md:h-[76px] md:flex-row md:items-center md:justify-between md:px-6 md:py-0">
				<div className="flex min-w-0 items-center gap-3">
					<VaayuMitraMark />
					<div className="flex min-w-0 flex-col justify-center gap-1">
						<span className="truncate text-lg font-semibold leading-none tracking-[-0.025em] text-foreground">
							VaayuMitra
						</span>
						<span className="truncate text-xs text-muted-foreground">
							IMD-grounded voice intelligence · Agora Conversational AI
						</span>
						{pipelineMetrics}
					</div>
				</div>

				<div className="flex items-center gap-2 md:pr-1">
					{statusPanel}
					<Button
						variant="destructive"
						size="sm"
						className="h-8 rounded-md border border-destructive bg-transparent px-3 text-xs font-medium text-destructive hover:bg-destructive/10"
						onClick={onEndConversation}
						aria-label="End conversation with AI agent"
						title="End conversation"
					>
						End Conversation
					</Button>
				</div>
			</header>

			<div className="flex min-h-0 w-full flex-1 flex-col gap-4 px-4 pb-4 pt-4 md:px-6 lg:flex-row lg:gap-0">
				<aside className="order-2 flex min-h-0 w-full shrink-0 flex-col gap-4 lg:order-1 lg:h-full lg:w-[26rem] lg:overflow-y-auto">
					<div className="h-64 min-h-0 shrink-0 lg:h-96 lg:flex-1">
						{transcriptPanel}
					</div>
					{imdSourceCard}
					{mapPanel}
				</aside>

				<main className="order-1 flex min-h-0 flex-1 flex-col lg:order-2 lg:border-l lg:border-border/80 lg:pl-6">
					<div className="flex min-h-0 flex-1 flex-col pb-2 pt-3 md:pb-6">
						<div className="flex min-h-0 flex-1 items-center justify-center">
							{visualizer}
						</div>
						{metricsOverlay ? <div className="shrink-0 pb-2">{metricsOverlay}</div> : null}
						<div className="shrink-0 pt-4">{controls}</div>
					</div>
				</main>
			</div>
		</div>
	);
}
